from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import (
    AIModelConfig,
    AIProcessingPolicy,
    Campaign,
    CampaignEvent,
    EventActor,
    EventObservable,
    EventTechnique,
    OperationJob,
    ThreatActor,
    ThreatEvent,
)
from apt_hunter.schemas.campaign import (
    CampaignAutomationStatus,
    CampaignBackfillRead,
    CampaignBackfillRequest,
    CampaignCreate,
    CampaignDetail,
    CampaignEventRead,
    CampaignEventUpsert,
    CampaignSummary,
    CampaignUpdate,
)
from apt_hunter.services.auth import AuthPrincipal
from apt_hunter.services.campaign_clustering import (
    campaign_automation_ready,
    pending_campaign_event_ids,
)
from apt_hunter.services.jobs import queue_job

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _actor(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    return principal.username if isinstance(principal, AuthPrincipal) else "local-admin"


def _campaign_metadata(
    session: Session,
    campaign_ids: list[UUID],
) -> tuple[dict[UUID, int], dict[UUID, list[str]], dict[UUID, list[str]]]:
    counts: dict[UUID, int] = {}
    stages: dict[UUID, list[str]] = defaultdict(list)
    actor_names: dict[UUID, list[str]] = defaultdict(list)
    if not campaign_ids:
        return counts, stages, actor_names
    for campaign_id, count in session.execute(
        select(CampaignEvent.campaign_id, func.count())
        .where(CampaignEvent.campaign_id.in_(campaign_ids))
        .group_by(CampaignEvent.campaign_id)
    ):
        counts[campaign_id] = int(count)
    for campaign_id, stage_name in session.execute(
        select(CampaignEvent.campaign_id, CampaignEvent.stage)
        .where(CampaignEvent.campaign_id.in_(campaign_ids))
        .distinct()
        .order_by(CampaignEvent.stage)
    ):
        stages[campaign_id].append(stage_name)
    for campaign_id, actor_name in session.execute(
        select(CampaignEvent.campaign_id, ThreatActor.canonical_name)
        .join(EventActor, EventActor.event_id == CampaignEvent.event_id)
        .join(ThreatActor, ThreatActor.id == EventActor.actor_id)
        .where(CampaignEvent.campaign_id.in_(campaign_ids))
        .distinct()
        .order_by(ThreatActor.canonical_name)
    ):
        actor_names[campaign_id].append(actor_name)
    return counts, stages, actor_names


def _campaign_summaries(
    session: Session,
    campaigns: list[Campaign],
) -> list[CampaignSummary]:
    counts, stages, actor_names = _campaign_metadata(
        session, [campaign.id for campaign in campaigns]
    )
    return [
        CampaignSummary(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            first_seen=campaign.first_seen,
            last_seen=campaign.last_seen,
            status=campaign.status,
            event_count=counts.get(campaign.id, 0),
            actor_names=actor_names[campaign.id],
            stages=stages[campaign.id],
            version=campaign.version,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        )
        for campaign in campaigns
    ]


def _refresh_campaign_bounds(session: Session, campaign: Campaign) -> None:
    events = list(
        session.scalars(
            select(ThreatEvent)
            .join(CampaignEvent, CampaignEvent.event_id == ThreatEvent.id)
            .where(CampaignEvent.campaign_id == campaign.id)
        )
    )
    observed = [event.first_seen or event.created_at for event in events]
    last_observed = [event.last_seen or event.first_seen or event.created_at for event in events]
    campaign.first_seen = min(observed) if observed else None
    campaign.last_seen = max(last_observed) if last_observed else None


def _campaign_detail(session: Session, campaign: Campaign) -> CampaignDetail:
    summary = _campaign_summaries(session, [campaign])[0]
    rows = list(
        session.execute(
            select(CampaignEvent, ThreatEvent)
            .join(ThreatEvent, ThreatEvent.id == CampaignEvent.event_id)
            .where(CampaignEvent.campaign_id == campaign.id)
            .order_by(ThreatEvent.first_seen.asc().nullslast(), ThreatEvent.created_at.asc())
        )
    )
    event_ids = [event.id for _, event in rows]
    actors: dict[UUID, list[str]] = defaultdict(list)
    if event_ids:
        for event_id, actor_name in session.execute(
            select(EventActor.event_id, ThreatActor.canonical_name)
            .join(ThreatActor, ThreatActor.id == EventActor.actor_id)
            .where(EventActor.event_id.in_(event_ids))
            .order_by(ThreatActor.canonical_name)
        ):
            actors[event_id].append(actor_name)
    return CampaignDetail(
        **summary.model_dump(),
        events=[
            CampaignEventRead(
                event_id=event.id,
                event_title=event.title,
                event_summary=event.summary,
                event_first_seen=event.first_seen,
                event_last_seen=event.last_seen,
                stage=membership.stage,
                confidence=membership.confidence,
                evidence_note=membership.evidence_note,
                reviewed_at=membership.reviewed_at,
                reviewed_by=membership.reviewed_by,
                actor_names=actors[event.id],
            )
            for membership, event in rows
        ],
    )


@router.get("", response_model=list[CampaignSummary])
def list_campaigns(
    session: DbSession,
    q: str | None = Query(default=None, max_length=300),
    campaign_status: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[CampaignSummary]:
    statement = select(Campaign)
    if q:
        statement = statement.where(func.lower(Campaign.name).contains(q.strip().casefold()))
    if campaign_status:
        statement = statement.where(Campaign.status == campaign_status)
    campaigns = list(
        session.scalars(
            statement.order_by(
                Campaign.last_seen.desc().nullslast(), Campaign.created_at.desc()
            ).limit(limit)
        )
    )
    return _campaign_summaries(session, campaigns)


@router.get("/automation/status", response_model=CampaignAutomationStatus)
def get_campaign_automation_status(session: DbSession) -> CampaignAutomationStatus:
    policy = session.get(AIProcessingPolicy, "default")
    confirmed_event_count = int(
        session.scalar(
            select(func.count())
            .select_from(ThreatEvent)
            .where(
                ThreatEvent.status == "confirmed",
                ThreatEvent.superseded_by_id.is_(None),
            )
        )
        or 0
    )
    assigned_event_count = int(
        session.scalar(
            select(func.count(func.distinct(CampaignEvent.event_id)))
            .select_from(CampaignEvent)
            .join(ThreatEvent, ThreatEvent.id == CampaignEvent.event_id)
            .where(
                ThreatEvent.status == "confirmed",
                ThreatEvent.superseded_by_id.is_(None),
            )
        )
        or 0
    )
    eligibility = (
        func.coalesce(ThreatEvent.confidence_analyst, ThreatEvent.confidence_auto, 0) >= 70,
        exists().where(EventActor.event_id == ThreatEvent.id),
        (
            exists().where(EventObservable.event_id == ThreatEvent.id)
            | exists().where(EventTechnique.event_id == ThreatEvent.id)
        ),
    )
    eligible_event_count = int(
        session.scalar(
            select(func.count())
            .select_from(ThreatEvent)
            .where(
                ThreatEvent.status == "confirmed",
                ThreatEvent.superseded_by_id.is_(None),
                *eligibility,
            )
        )
        or 0
    )
    eligible_unassigned_count = int(
        session.scalar(
            select(func.count())
            .select_from(ThreatEvent)
            .where(
                ThreatEvent.status == "confirmed",
                ThreatEvent.superseded_by_id.is_(None),
                *eligibility,
                ~exists().where(CampaignEvent.event_id == ThreatEvent.id),
            )
        )
        or 0
    )
    campaign_count = int(session.scalar(select(func.count()).select_from(Campaign)) or 0)
    pending_job_count = int(
        session.scalar(
            select(func.count())
            .select_from(OperationJob)
            .where(
                OperationJob.job_type == "campaign_clustering",
                OperationJob.status.in_(["queued", "running"]),
            )
        )
        or 0
    )
    model_configured = bool(
        session.scalar(
            select(AIModelConfig.id).where(
                AIModelConfig.enabled.is_(True), AIModelConfig.is_default.is_(True)
            )
        )
    )
    last_job = session.scalar(
        select(OperationJob)
        .where(OperationJob.job_type == "campaign_clustering")
        .order_by(OperationJob.created_at.desc())
        .limit(1)
    )
    return CampaignAutomationStatus(
        automation_enabled=bool(policy and policy.automation_enabled),
        unattended_mode=bool(policy and policy.unattended_mode),
        model_configured=model_configured,
        ready=campaign_automation_ready(session),
        confirmed_event_count=confirmed_event_count,
        eligible_event_count=eligible_event_count,
        assigned_event_count=assigned_event_count,
        unassigned_event_count=eligible_unassigned_count,
        campaign_count=campaign_count,
        pending_job_count=pending_job_count,
        last_job_status=last_job.status if last_job else None,
        last_job_at=last_job.created_at if last_job else None,
        last_job_result=last_job.result if last_job else {},
        last_job_error=last_job.error if last_job else None,
    )


@router.post("/automation/backfill", response_model=CampaignBackfillRead)
def backfill_campaigns(
    payload: CampaignBackfillRequest,
    request: Request,
    session: DbSession,
) -> CampaignBackfillRead:
    if not campaign_automation_ready(session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="请先启用无人值守AI自动化并配置可用的默认模型",
        )
    event_ids = pending_campaign_event_ids(
        session,
        limit=payload.limit,
        force=payload.force,
    )
    job_ids = [
        queue_job(
            job_type="campaign_clustering",
            subject_type="event",
            subject_id=event_id,
            requested_by=_actor(request),
        )
        for event_id in event_ids
    ]
    return CampaignBackfillRead(queued=len(job_ids), job_ids=job_ids)


@router.post("", response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, session: DbSession) -> CampaignDetail:
    if (
        payload.first_seen is not None
        and payload.last_seen is not None
        and payload.last_seen < payload.first_seen
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="last_seen must be on or after first_seen",
        )
    existing = session.scalar(
        select(Campaign).where(func.lower(Campaign.name) == payload.name.strip().casefold())
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign name already exists",
        )
    campaign = Campaign(
        name=payload.name.strip(),
        description=payload.description.strip(),
        first_seen=payload.first_seen,
        last_seen=payload.last_seen,
        status=payload.status,
    )
    session.add(campaign)
    session.commit()
    return _campaign_detail(session, campaign)


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(campaign_id: UUID, session: DbSession) -> CampaignDetail:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _campaign_detail(session, campaign)


@router.patch("/{campaign_id}", response_model=CampaignDetail)
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    session: DbSession,
) -> CampaignDetail:
    campaign = session.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign changed; reload before updating",
        )
    if payload.name is not None:
        duplicate = session.scalar(
            select(Campaign).where(
                Campaign.id != campaign_id,
                func.lower(Campaign.name) == payload.name.strip().casefold(),
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign name already exists",
            )
        campaign.name = payload.name.strip()
    if payload.description is not None:
        campaign.description = payload.description.strip()
    if payload.status is not None:
        campaign.status = payload.status
    campaign.version += 1
    session.commit()
    return _campaign_detail(session, campaign)


@router.post("/{campaign_id}/events", response_model=CampaignDetail)
def upsert_campaign_event(
    campaign_id: UUID,
    payload: CampaignEventUpsert,
    session: DbSession,
) -> CampaignDetail:
    campaign = session.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign changed; reload before assigning an event",
        )
    event = session.scalar(
        select(ThreatEvent).where(ThreatEvent.id == payload.event_id).with_for_update()
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status != "confirmed" or event.superseded_by_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only current confirmed events can be assigned to a Campaign",
        )
    membership = session.get(CampaignEvent, (campaign_id, payload.event_id))
    now = datetime.now(UTC)
    if membership is None:
        membership = CampaignEvent(
            campaign_id=campaign_id,
            event_id=payload.event_id,
            stage=payload.stage,
            confidence=payload.confidence,
            evidence_note=payload.evidence_note.strip(),
            reviewed_at=now,
            reviewed_by=payload.reviewed_by,
        )
        session.add(membership)
    else:
        membership.stage = payload.stage
        membership.confidence = payload.confidence
        membership.evidence_note = payload.evidence_note.strip()
        membership.reviewed_at = now
        membership.reviewed_by = payload.reviewed_by
    campaign.version += 1
    session.flush()
    _refresh_campaign_bounds(session, campaign)
    session.commit()
    return _campaign_detail(session, campaign)


@router.delete(
    "/{campaign_id}/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_campaign_event(
    campaign_id: UUID,
    event_id: UUID,
    session: DbSession,
    expected_version: int = Query(ge=1),
) -> Response:
    campaign = session.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign changed; reload before removing an event",
        )
    membership = session.get(CampaignEvent, (campaign_id, event_id))
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign event membership not found",
        )
    session.delete(membership)
    campaign.version += 1
    session.flush()
    _refresh_campaign_bounds(session, campaign)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
