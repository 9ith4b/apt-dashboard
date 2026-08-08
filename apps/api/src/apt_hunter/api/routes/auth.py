from datetime import timedelta
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis import Redis
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apt_hunter.config import get_settings
from apt_hunter.db.session import get_db
from apt_hunter.models import AuditLog, User, UserSession
from apt_hunter.schemas.auth import (
    AuditLogRead,
    AuthSessionRead,
    CsrfRead,
    LoginRequest,
    UserCreate,
    UserRead,
    UserRole,
    UserUpdate,
)
from apt_hunter.services.auth import (
    DUMMY_PASSWORD_HASH,
    AuthPrincipal,
    create_session,
    hash_password,
    utc_now,
    verify_password,
    write_audit_log,
)

router = APIRouter()
audit_router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _principal(request: Request) -> AuthPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthPrincipal):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return principal


CurrentPrincipal = Annotated[AuthPrincipal, Depends(_principal)]


def _user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=cast(UserRole, user.role),
        enabled=user.enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_key(request: Request, username: str) -> str:
    from hashlib import sha256

    fingerprint = sha256(f"{_client_ip(request)}:{username}".encode()).hexdigest()
    return f"apt-hunter:auth:login:{fingerprint}"


def _rate_count(request: Request, username: str) -> int:
    settings = get_settings()
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        value = client.get(_rate_key(request, username))
        return int(value) if isinstance(value, (bytes, str, int)) else 0
    except Exception:
        return 0


def _record_failure(request: Request, username: str) -> None:
    settings = get_settings()
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        key = _rate_key(request, username)
        with client.pipeline() as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, settings.login_window_seconds)
            pipeline.execute()
    except Exception:
        return


def _clear_failures(request: Request, username: str) -> None:
    settings = get_settings()
    try:
        Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        ).delete(_rate_key(request, username))
    except Exception:
        return


def _audit_login(
    session: Session,
    request: Request,
    *,
    user_id: UUID | None,
    username: str,
    result: str,
) -> None:
    write_audit_log(
        session,
        actor_user_id=user_id,
        action="auth.login",
        result=result,
        request_id=getattr(request.state, "request_id", "unknown"),
        ip_address=_client_ip(request),
        object_type="user",
        object_id=str(user_id) if user_id else None,
        details={"username": username},
    )


@router.post("/login", response_model=AuthSessionRead)
def login(
    payload: LoginRequest, request: Request, response: Response, session: DbSession
) -> AuthSessionRead:
    settings = get_settings()
    username = payload.username
    user = session.scalar(select(User).where(User.username == username))
    now = utc_now()
    if _rate_count(request, username) >= settings.login_attempt_limit:
        _audit_login(
            session,
            request,
            user_id=user.id if user else None,
            username=username,
            result="rate_limited",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Login temporarily unavailable"
        )
    locked = bool(user and user.locked_until and user.locked_until > now)
    candidate_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(candidate_hash, payload.password)
    valid = bool(user and user.enabled and not locked and password_valid)
    if not valid:
        _record_failure(request, username)
        if user and user.enabled:
            user.failed_attempts += 1
            if user.failed_attempts >= settings.login_attempt_limit:
                user.locked_until = now + timedelta(seconds=settings.login_window_seconds)
            session.commit()
        _audit_login(
            session,
            request,
            user_id=user.id if user else None,
            username=username,
            result="denied",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    user_session, raw_token = create_session(
        session,
        user,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        ttl_hours=settings.session_ttl_hours,
    )
    session.commit()
    session.refresh(user_session)
    _clear_failures(request, username)
    _audit_login(session, request, user_id=user.id, username=username, result="succeeded")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_secure_cookie,
        samesite="lax",
        path="/",
    )
    return AuthSessionRead(user=_user_read(user), expires_at=user_session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    principal: CurrentPrincipal,
    session: DbSession,
) -> None:
    user_session = session.get(UserSession, principal.session_id)
    if user_session and user_session.revoked_at is None:
        user_session.revoked_at = utc_now()
        session.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")


@router.get("/me", response_model=AuthSessionRead)
def me(principal: CurrentPrincipal, session: DbSession) -> AuthSessionRead:
    user = session.get(User, principal.user_id)
    if user is None or not user.enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return AuthSessionRead(user=_user_read(user), expires_at=principal.expires_at)


@router.get("/csrf", response_model=CsrfRead)
def csrf(principal: CurrentPrincipal) -> CsrfRead:
    return CsrfRead(csrf_token=principal.csrf_token)


@router.get("/users", response_model=list[UserRead])
def list_users(session: DbSession) -> list[UserRead]:
    return [_user_read(user) for user in session.scalars(select(User).order_by(User.username))]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: DbSession) -> UserRead:
    user = User(
        username=payload.username,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        enabled=payload.enabled,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        ) from exc
    session.refresh(user)
    return _user_read(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, session: DbSession) -> UserRead:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if user.role == "admin" and (
        changes.get("enabled") is False or ("role" in changes and changes.get("role") != "admin")
    ):
        enabled_admins = session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.enabled.is_(True))
        )
        if enabled_admins == 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last enabled admin cannot be disabled or demoted",
            )
    if "password" in changes:
        user.password_hash = hash_password(str(changes.pop("password")))
        user.failed_attempts = 0
        user.locked_until = None
        session.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
    for field, value in changes.items():
        setattr(user, field, value.strip() if field == "display_name" else value)
    session.commit()
    session.refresh(user)
    return _user_read(user)


@audit_router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    session: DbSession,
    action: str | None = None,
    result: str | None = None,
    limit: int = 100,
) -> list[AuditLogRead]:
    limit = min(max(limit, 1), 500)
    statement = (
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        statement = statement.where(AuditLog.action == action)
    if result:
        statement = statement.where(AuditLog.result == result)
    return [
        AuditLogRead(
            id=log.id,
            actor_user_id=log.actor_user_id,
            actor_username=username,
            action=log.action,
            object_type=log.object_type,
            object_id=log.object_id,
            result=log.result,
            request_id=log.request_id,
            ip_address=log.ip_address,
            details=log.details,
            created_at=log.created_at,
        )
        for log, username in session.execute(statement)
    ]
