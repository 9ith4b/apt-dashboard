from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.models import (
    AIModelConfig,
    AIProcessingPolicy,
    Campaign,
    CampaignEvent,
    EventReport,
    Report,
    ReportAnalysis,
    Source,
    ThreatEvent,
)
from apt_hunter.services.actor_normalization import sync_event_actors_from_reports
from apt_hunter.services.ai_gateway import AICampaignDecision
from apt_hunter.services.campaign_clustering import cluster_event
from apt_hunter.services.knowledge import persist_report_knowledge, sync_event_knowledge


def _add_event(
    session: Session,
    *,
    source: Source,
    index: int,
    title: str,
    actor: str,
    domain: str,
    observed_at: datetime,
) -> ThreatEvent:
    report = Report(
        source_id=source.id,
        title=title,
        canonical_url=f"https://vendor.example/report-{index}",
        normalized_text=f"{actor} used {domain} in a recruitment-themed intrusion.",
        exact_hash=str(index) * 64,
        relevance_score=95,
        relevance_reasons=["actor", "infrastructure"],
        status="approved",
        published_at=observed_at,
    )
    session.add(report)
    session.flush()
    session.add(
        ReportAnalysis(
            report_id=report.id,
            extraction_status="ready",
            review_status="approved",
            content_text=report.normalized_text,
            actors=[],
            capabilities=[],
            infrastructure=[],
            victims=[],
            reviewed_actors=[
                {
                    "name": actor,
                    "type": "threat-actor",
                    "confidence": 95,
                    "evidence": f"Attributed to {actor}.",
                }
            ],
            reviewed_capabilities=[],
            reviewed_infrastructure=[],
            reviewed_victims=[
                {
                    "name": "Software developers",
                    "type": "victim-sector",
                    "confidence": 90,
                    "evidence": "Developers were targeted.",
                }
            ],
        )
    )
    persist_report_knowledge(
        session,
        report_id=report.id,
        observed_at=observed_at,
        observables=[
            {
                "type": "domain",
                "value": domain,
                "normalized": domain,
                "scope": "public",
                "confidence": 98,
                "evidence": f"The intrusion used {domain}.",
                "start_offset": 10,
                "end_offset": 10 + len(domain),
            }
        ],
        techniques=[
            {
                "technique_id": "T1566.002",
                "name": "Spearphishing Link",
                "tactic": "initial-access",
                "confidence": 95,
                "evidence": "A recruitment link delivered the payload.",
                "start_offset": 0,
                "end_offset": 20,
            }
        ],
        method_version="ai-v3",
    )
    event = ThreatEvent(
        title=title,
        summary="Recruitment-themed developer targeting.",
        status="confirmed",
        confidence_auto=94,
        first_seen=observed_at,
        last_seen=observed_at,
    )
    session.add(event)
    session.flush()
    session.add(EventReport(event_id=event.id, report_id=report.id))
    session.flush()
    sync_event_actors_from_reports(session, event.id)
    sync_event_knowledge(session, event.id)
    return event


def test_ai_creates_campaign_from_two_linked_events_and_is_idempotent(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    observed_at = datetime(2026, 8, 1, 8, tzinfo=UTC)
    with Session(engine) as session:
        source = Source(type="rss", name="Vendor", url="https://vendor.example/feed")
        session.add(source)
        session.flush()
        first = _add_event(
            session,
            source=source,
            index=1,
            title="Lazarus fake interview delivers BeaverTail",
            actor="Lazarus Group",
            domain="jobs-example.com",
            observed_at=observed_at,
        )
        second = _add_event(
            session,
            source=source,
            index=2,
            title="Lazarus recruiter follow-up targets developers",
            actor="Lazarus Group",
            domain="jobs-example.com",
            observed_at=observed_at + timedelta(days=5),
        )
        _add_event(
            session,
            source=source,
            index=3,
            title="APT29 targets diplomats",
            actor="APT29",
            domain="diplomacy-example.com",
            observed_at=observed_at + timedelta(days=2),
        )
        session.add(
            AIModelConfig(
                name="Local model",
                provider="ollama",
                base_url="http://model.example/v1",
                model="test-model",
                enabled=True,
                is_default=True,
                updated_by="test",
            )
        )
        session.add(
            AIProcessingPolicy(
                key="default",
                automation_enabled=True,
                unattended_mode=True,
            )
        )
        session.commit()

        def decide(*_args, **kwargs):
            related_id = str(kwargs["event_candidates"][0]["id"])
            return (
                AICampaignDecision(
                    action="create_new",
                    campaign_name="Operation Dream Job",
                    description="Lazarus recruitment-themed intrusion activity.",
                    stage="initial-access",
                    confidence=93,
                    evidence_note="Shared actor, dedicated domain, victim profile and lure theme.",
                    related_event_ids=[related_id],
                    decision_reason="Two distinct events form one sustained operation.",
                ),
                42,
            )

        monkeypatch.setattr(
            "apt_hunter.services.campaign_clustering.analyze_campaign_with_model",
            decide,
        )
        result = cluster_event(session, first.id)
        session.commit()

        assert result["status"] == "created"
        campaign = session.scalar(select(Campaign))
        assert campaign is not None
        assert campaign.name == "Operation Dream Job"
        memberships = list(
            session.scalars(select(CampaignEvent).where(CampaignEvent.campaign_id == campaign.id))
        )
        assert {item.event_id for item in memberships} == {first.id, second.id}
        assert all(item.reviewed_by == "campaign-clustering-v1" for item in memberships)

        repeated = cluster_event(session, first.id)
        assert repeated == {
            "status": "already_assigned",
            "campaign_id": str(campaign.id),
        }
    Base.metadata.drop_all(engine)
