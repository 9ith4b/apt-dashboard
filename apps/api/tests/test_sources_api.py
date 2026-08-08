from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.db.session import get_db
from apt_hunter.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_source_crud_and_duplicate_protection(client: TestClient) -> None:
    payload = {
        "name": "CISA Advisories",
        "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "poll_interval_minutes": 30,
        "enabled": True,
    }
    created = client.post("/api/v1/sources", json=payload)

    assert created.status_code == 201
    source = created.json()
    assert source["type"] == "rss"
    assert source["health_status"] == "pending"
    assert source["report_count"] == 0

    listed = client.get("/api/v1/sources")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["CISA Advisories"]

    disabled = client.patch(
        f"/api/v1/sources/{source['id']}",
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["health_status"] == "disabled"
    assert disabled.json()["next_poll_at"] is None

    duplicate = client.post("/api/v1/sources", json=payload)
    assert duplicate.status_code == 409


def test_source_validation_rejects_unsafe_url(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "name": "Unsafe feed",
            "url": "file:///etc/passwd",
        },
    )

    assert response.status_code == 422
