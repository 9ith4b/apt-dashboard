from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import ThreatEvent, WatchRule, WatchRuleHit
from apt_hunter.schemas.watch import (
    WatchConditions,
    WatchRuleCreate,
    WatchRuleEvaluationRead,
    WatchRuleHitRead,
    WatchRulePreviewRead,
    WatchRuleRead,
    WatchRuleUpdate,
)
from apt_hunter.services.watch_rules import evaluate_rule, preview_matches

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _rule_or_404(session: Session, rule_id: UUID) -> WatchRule:
    rule = session.get(WatchRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch rule not found")
    return rule


def _read(rule: WatchRule, hit_count: int = 0) -> WatchRuleRead:
    return WatchRuleRead.model_validate(rule, from_attributes=True).model_copy(
        update={"hit_count": hit_count}
    )


@router.get("", response_model=list[WatchRuleRead])
def list_watch_rules(session: DbSession) -> list[WatchRuleRead]:
    rows = session.execute(
        select(WatchRule, func.count(WatchRuleHit.id))
        .outerjoin(WatchRuleHit, WatchRuleHit.rule_id == WatchRule.id)
        .group_by(WatchRule.id)
        .order_by(WatchRule.created_at.desc())
    )
    return [_read(rule, int(hit_count)) for rule, hit_count in rows]


@router.post("", response_model=WatchRuleRead, status_code=status.HTTP_201_CREATED)
def create_watch_rule(payload: WatchRuleCreate, session: DbSession) -> WatchRuleRead:
    rule = WatchRule(
        name=payload.name.strip(),
        description=payload.description.strip(),
        conditions=payload.conditions.model_dump(),
        severity=payload.severity,
        enabled=payload.enabled,
        created_by=payload.created_by,
    )
    session.add(rule)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A watch rule with this name already exists",
        ) from error
    session.refresh(rule)
    return _read(rule)


@router.post("/preview", response_model=WatchRulePreviewRead)
def preview_new_watch_rule(
    payload: WatchRuleCreate,
    session: DbSession,
) -> WatchRulePreviewRead:
    matches = preview_matches(session, payload.conditions)
    return WatchRulePreviewRead(match_count=len(matches), matches=matches)


@router.patch("/{rule_id}", response_model=WatchRuleRead)
def update_watch_rule(
    rule_id: UUID,
    payload: WatchRuleUpdate,
    session: DbSession,
) -> WatchRuleRead:
    changes = payload.model_dump(exclude={"expected_version"}, exclude_unset=True)
    if "conditions" in changes and payload.conditions is not None:
        changes["conditions"] = payload.conditions.model_dump()
    if "name" in changes and isinstance(changes["name"], str):
        changes["name"] = changes["name"].strip()
    changes["version"] = WatchRule.version + 1
    updated_id = session.scalar(
        update(WatchRule)
        .where(WatchRule.id == rule_id, WatchRule.version == payload.expected_version)
        .values(**changes)
        .returning(WatchRule.id)
    )
    if updated_id is None:
        session.rollback()
        if session.get(WatchRule, rule_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watch rule not found"
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This watch rule changed in another session; reload before saving",
        )
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A watch rule with this name already exists",
        ) from error
    return _read(_rule_or_404(session, rule_id))


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watch_rule(
    rule_id: UUID,
    session: DbSession,
    expected_version: int = Query(ge=1),
) -> Response:
    deleted_id = session.scalar(
        delete(WatchRule)
        .where(WatchRule.id == rule_id, WatchRule.version == expected_version)
        .returning(WatchRule.id)
    )
    if deleted_id is None:
        session.rollback()
        if session.get(WatchRule, rule_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watch rule not found"
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This watch rule changed in another session; reload before deleting",
        )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{rule_id}/hits", response_model=list[WatchRuleHitRead])
def list_watch_rule_hits(
    rule_id: UUID,
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[WatchRuleHitRead]:
    _rule_or_404(session, rule_id)
    rows = session.execute(
        select(WatchRuleHit, ThreatEvent.title)
        .join(ThreatEvent, ThreatEvent.id == WatchRuleHit.subject_id)
        .where(WatchRuleHit.rule_id == rule_id)
        .order_by(WatchRuleHit.created_at.desc())
        .limit(limit)
    )
    return [
        WatchRuleHitRead(
            id=hit.id,
            rule_id=hit.rule_id,
            subject_type=hit.subject_type,
            subject_id=hit.subject_id,
            subject_title=title,
            matched_on=hit.matched_on,
            created_at=hit.created_at,
        )
        for hit, title in rows
    ]


@router.post("/{rule_id}/preview", response_model=WatchRulePreviewRead)
def preview_watch_rule(rule_id: UUID, session: DbSession) -> WatchRulePreviewRead:
    rule = _rule_or_404(session, rule_id)
    matches = preview_matches(
        session,
        WatchConditions.model_validate(rule.conditions),
        rule_id=rule.id,
    )
    return WatchRulePreviewRead(rule_id=rule.id, match_count=len(matches), matches=matches)


@router.post("/{rule_id}/evaluate", response_model=WatchRuleEvaluationRead)
def evaluate_watch_rule(rule_id: UUID, session: DbSession) -> WatchRuleEvaluationRead:
    rule = _rule_or_404(session, rule_id)
    evaluated, created = evaluate_rule(session, rule)
    session.commit()
    hit_count = session.scalar(
        select(func.count(WatchRuleHit.id)).where(WatchRuleHit.rule_id == rule.id)
    )
    return WatchRuleEvaluationRead(
        rule_id=rule.id,
        evaluated_count=evaluated,
        created_hit_count=created,
        hit_count=int(hit_count or 0),
    )
