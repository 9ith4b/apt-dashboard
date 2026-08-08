from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import Notification
from apt_hunter.schemas.watch import NotificationListRead, NotificationRead

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=NotificationListRead)
def list_notifications(
    session: DbSession,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationListRead:
    statement = select(Notification)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    items = list(session.scalars(statement.order_by(Notification.created_at.desc()).limit(limit)))
    unread_count = session.scalar(
        select(func.count(Notification.id)).where(Notification.read_at.is_(None))
    )
    return NotificationListRead(
        unread_count=int(unread_count or 0),
        items=[NotificationRead.model_validate(item, from_attributes=True) for item in items],
    )


@router.post("/read-all", response_model=NotificationListRead)
def mark_all_notifications_read(session: DbSession) -> NotificationListRead:
    session.execute(
        update(Notification).where(Notification.read_at.is_(None)).values(read_at=datetime.now(UTC))
    )
    session.commit()
    return list_notifications(session)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: UUID,
    session: DbSession,
) -> NotificationRead:
    notification = session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        session.commit()
        session.refresh(notification)
    return NotificationRead.model_validate(notification, from_attributes=True)
