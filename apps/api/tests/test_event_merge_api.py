from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.db.session import get_db
from apt_hunter.main import app
from apt_hunter.models import EventReport, Report, ReportAnalysis, Source, ThreatEvent
from apt_hunter.services.actor_normalization import sync_event_actors_from_reports
from apt_hunter.services.event_clustering import generate_merge_candidates
from apt_hunter.services.knowledge import persist_report_knowledge, sync_event_knowledge


@pytest.fixture
def merge_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    observed_at = datetime(2026, 8, 1, 8, tzinfo=UTC)
    with testing_session.begin() as session:
        sources = [
            Source(type="rss", name="Vendor One", url="https://one.example/feed"),
            Source(type="rss", name="Vendor Two", url="https://two.example/feed"),
        ]
        session.add_all(sources)
        session.flush()
        reports: list[Report] = []
        for index, source in enumerate(sources):
            report = Report(
                source_id=source.id,
                title=f"APT29 diplomatic phishing campaign report {index + 1}",
                canonical_url=f"https://{index + 1}.example/report",
                normalized_text="APT29 targeted diplomats with spearphishing.",
                exact_hash=str(index + 1) * 64,
                relevance_score=95,
                relevance_reasons=["actor", "shared infrastructure"],
                status="approved",
                published_at=observed_at + timedelta(days=index),
            )
            session.add(report)
            session.flush()
            session.add(
                ReportAnalysis(
                    report_id=report.id,
                    extraction_status="ready",
                    review_status="approved",
                    content_text="APT29 used evil-example.com and T1566.001 against diplomats.",
                    actors=[],
                    capabilities=[],
                    infrastructure=[],
                    victims=[],
                    reviewed_actors=[
                        {
                            "name": "APT29",
                            "type": "threat-actor",
                            "confidence": 95,
                            "evidence": "APT29 attribution.",
                        }
                    ],
                    reviewed_capabilities=[],
                    reviewed_infrastructure=[],
                    reviewed_victims=[
                        {
                            "name": "Diplomats",
                            "type": "victim-sector",
                            "confidence": 90,
                            "evidence": "Diplomatic targets.",
                        }
                    ],
                )
            )
            persist_report_knowledge(
                session,
                report_id=report.id,
                observed_at=report.published_at or observed_at,
                observables=[
                    {
                        "type": "domain",
                        "value": "evil-example.com",
                        "normalized": "evil-example.com",
                        "scope": "public",
                        "confidence": 98,
                        "evidence": "APT29 used evil-example.com.",
                        "start_offset": 11,
                        "end_offset": 27,
                    }
                ],
                techniques=[
                    {
                        "technique_id": "T1566.001",
                        "name": "MITRE ATT&CK T1566.001",
                        "tactic": None,
                        "confidence": 99,
                        "evidence": "The report cites T1566.001.",
                        "start_offset": 32,
                        "end_offset": 41,
                    }
                ],
                method_version="rules-v2",
            )
            reports.append(report)

        target = ThreatEvent(
            title="APT29 diplomatic phishing campaign",
            summary="First vendor report.",
            status="confirmed",
            first_seen=observed_at,
            last_seen=observed_at,
        )
        source = ThreatEvent(
            title="APT29 targets diplomats with phishing",
            summary="Second vendor report.",
            status="confirmed",
            first_seen=observed_at + timedelta(days=1),
            last_seen=observed_at + timedelta(days=1),
        )
        session.add_all([target, source])
        session.flush()
        session.add_all(
            [
                EventReport(event_id=target.id, report_id=reports[0].id),
                EventReport(event_id=source.id, report_id=reports[1].id),
            ]
        )
        session.flush()
        for event in (target, source):
            sync_event_actors_from_reports(session, event.id)
            sync_event_knowledge(session, event.id)
        session.flush()
        assert generate_merge_candidates(session, source.id) == 1

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_merge_candidate_can_be_approved_and_undone(merge_client: TestClient) -> None:
    listed = merge_client.get("/api/v1/events/merge-candidates")

    assert listed.status_code == 200
    candidate = listed.json()[0]
    assert candidate["score"] >= 45
    assert candidate["features"]["observable_overlap"] == 1

    approved = merge_client.post(
        f"/api/v1/events/merge-candidates/{candidate['id']}/decision",
        json={
            "decision": "approved",
            "reason": "Both reports share attribution, infrastructure, and technique.",
            "expected_version": candidate["version"],
        },
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    events = merge_client.get("/api/v1/events").json()
    assert len(events) == 1
    assert events[0]["report_count"] == 2
    detail = merge_client.get(f"/api/v1/events/{events[0]['id']}").json()
    assert len(detail["reports"]) == 2
    assert detail["observable_count"] == 1

    undone = merge_client.post(
        f"/api/v1/events/merge-candidates/{candidate['id']}/undo",
        json={"expected_version": approved.json()["version"]},
    )

    assert undone.status_code == 200
    assert undone.json()["status"] == "undone"
    assert len(merge_client.get("/api/v1/events").json()) == 2


def test_merge_candidate_reject_is_version_checked(merge_client: TestClient) -> None:
    candidate = merge_client.get("/api/v1/events/merge-candidates").json()[0]
    rejected = merge_client.post(
        f"/api/v1/events/merge-candidates/{candidate['id']}/decision",
        json={
            "decision": "rejected",
            "reason": "The victim scope is materially different.",
            "expected_version": candidate["version"],
        },
    )
    stale = merge_client.post(
        f"/api/v1/events/merge-candidates/{candidate['id']}/decision",
        json={
            "decision": "approved",
            "expected_version": candidate["version"],
        },
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert stale.status_code == 409
