from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.models import AuditLog, User, UserSession

PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("invalid-login-timing-sentinel")


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: UUID
    session_id: UUID
    username: str
    display_name: str
    role: str
    csrf_token: str
    expires_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(
    session: Session,
    user: User,
    *,
    ip_address: str,
    user_agent: str,
    ttl_hours: int,
) -> tuple[UserSession, str]:
    now = utc_now()
    raw_token = secrets.token_urlsafe(48)
    user_session = UserSession(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        csrf_token=secrets.token_urlsafe(32),
        expires_at=now + timedelta(hours=ttl_hours),
        last_seen_at=now,
        ip_address=ip_address,
        user_agent=user_agent[:500],
    )
    session.add(user_session)
    session.flush()
    return user_session, raw_token


def load_principal(session: Session, raw_token: str) -> AuthPrincipal | None:
    now = utc_now()
    row = session.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_hash == token_hash(raw_token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            User.enabled.is_(True),
        )
    ).one_or_none()
    if row is None:
        return None
    user_session, user = row
    user_session.last_seen_at = now
    session.commit()
    return AuthPrincipal(
        user_id=user.id,
        session_id=user_session.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        csrf_token=user_session.csrf_token,
        expires_at=user_session.expires_at,
    )


def write_audit_log(
    session: Session,
    *,
    actor_user_id: UUID | None,
    action: str,
    result: str,
    request_id: str,
    ip_address: str,
    object_type: str | None = None,
    object_id: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action[:100],
            object_type=object_type[:100] if object_type else None,
            object_id=object_id[:100] if object_id else None,
            result=result[:32],
            request_id=request_id[:64],
            ip_address=ip_address[:64],
            details=details or {},
        )
    )
    session.commit()
