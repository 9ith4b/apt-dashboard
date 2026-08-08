from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.api.routes import auth as auth_routes
from apt_hunter.config import get_settings
from apt_hunter.db.base import Base
from apt_hunter.db.session import get_db
from apt_hunter.main import create_app
from apt_hunter.models import AuditLog, User
from apt_hunter.services.auth import hash_password, verify_password

ORIGIN = "http://testserver"


@pytest.fixture
def secure_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with testing_session.begin() as session:
        session.add_all(
            [
                User(
                    username="admin",
                    display_name="Security Admin",
                    password_hash=hash_password("correct horse battery staple"),
                    role="admin",
                    enabled=True,
                ),
                User(
                    username="viewer",
                    display_name="Read Only",
                    password_hash=hash_password("viewer password is long"),
                    role="viewer",
                    enabled=True,
                ),
            ]
        )

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    monkeypatch.setenv("APT_HUNTER_AUTH_ENABLED", "true")
    monkeypatch.setenv("APT_HUNTER_SESSION_SECURE_COOKIE", "false")
    get_settings.cache_clear()
    monkeypatch.setattr("apt_hunter.security.SessionLocal", testing_session)
    monkeypatch.setattr(auth_routes, "_rate_count", lambda *_: 0)
    monkeypatch.setattr(auth_routes, "_record_failure", lambda *_: None)
    monkeypatch.setattr(auth_routes, "_clear_failures", lambda *_: None)
    test_app = create_app()
    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app, base_url=ORIGIN) as client:
        yield client, testing_session
    get_settings.cache_clear()
    Base.metadata.drop_all(engine)


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    csrf = client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200
    return str(csrf.json()["csrf_token"])


def test_argon2id_password_hashing() -> None:
    hashed = hash_password("a sufficiently long password")

    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "a sufficiently long password") is True
    assert verify_password(hashed, "wrong password") is False


def test_login_csrf_admin_authorization_and_audit(
    secure_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = secure_client
    csrf = _login(client, "admin", "correct horse battery staple")
    me = client.get("/api/v1/auth/me")
    assert me.json()["user"]["role"] == "admin"

    payload = {
        "name": "Security Research",
        "url": "https://example.com/feed.xml",
        "enabled": False,
    }
    assert (
        client.post("/api/v1/sources", headers={"Origin": ORIGIN}, json=payload).status_code == 403
    )
    created = client.post(
        "/api/v1/sources",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json=payload,
    )
    assert created.status_code == 201
    assert created.headers["x-content-type-options"] == "nosniff"
    assert created.headers["x-frame-options"] == "DENY"

    logs = client.get("/api/v1/audit-logs")
    assert logs.status_code == 200
    assert any(item["action"] == "POST sources" for item in logs.json())
    with testing_session() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.result == "csrf_denied"))


def test_viewer_can_read_but_cannot_modify(
    secure_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = secure_client
    csrf = _login(client, "viewer", "viewer password is long")

    assert client.get("/api/v1/sources").status_code == 200
    denied = client.post(
        "/api/v1/sources",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"name": "Denied", "url": "https://example.com/feed"},
    )
    assert denied.status_code == 403
    assert client.get("/api/v1/audit-logs").status_code == 403


def test_login_rejects_missing_origin_and_uses_generic_failure(
    secure_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = secure_client
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "correct horse battery staple"},
        ).status_code
        == 403
    )
    unknown = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": "missing", "password": "not the right password"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "Invalid username or password"


def test_unknown_user_still_runs_password_verification(
    secure_client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = secure_client
    verified_hashes: list[str] = []

    def fake_verify(password_hash: str, password: str) -> bool:
        verified_hashes.append(password_hash)
        return False

    monkeypatch.setattr(auth_routes, "verify_password", fake_verify)
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": "missing", "password": "not the right password"},
    )

    assert response.status_code == 401
    assert verified_hashes == [auth_routes.DUMMY_PASSWORD_HASH]
