from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
from apt_hunter.services.knowledge import persist_report_knowledge, sync_event_knowledge


@pytest.fixture
def hunt_campaign_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    observed_at = datetime(2026, 8, 1, 8, tzinfo=UTC)
    with testing_session.begin() as session:
        source = Source(type="rss", name="Vendor Research", url="https://vendor.example/feed")
        session.add(source)
        session.flush()
        report = Report(
            source_id=source.id,
            title="Lazarus fake interview campaign",
            canonical_url="https://vendor.example/lazarus",
            normalized_text="Lazarus used interview-example.com to target developers.",
            exact_hash="7" * 64,
            relevance_score=96,
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
                        "name": "Lazarus Group",
                        "type": "threat-actor",
                        "confidence": 95,
                        "evidence": "The report attributes the activity to Lazarus.",
                    }
                ],
                reviewed_capabilities=[],
                reviewed_infrastructure=[],
                reviewed_victims=[],
            )
        )
        persist_report_knowledge(
            session,
            report_id=report.id,
            observed_at=observed_at,
            observables=[
                {
                    "type": "domain",
                    "value": "interview-example.com",
                    "normalized": "interview-example.com",
                    "scope": "public",
                    "confidence": 98,
                    "evidence": "Lazarus used interview-example.com to deliver malware.",
                    "start_offset": 13,
                    "end_offset": 34,
                }
            ],
            techniques=[],
            method_version="rules-v2",
        )
        event = ThreatEvent(
            title="Lazarus fake interview campaign",
            summary="Developers were targeted with malicious interview exercises.",
            status="confirmed",
            confidence_analyst=95,
            first_seen=observed_at,
            last_seen=observed_at,
        )
        session.add(event)
        session.flush()
        session.add(EventReport(event_id=event.id, report_id=report.id))
        session.flush()
        sync_event_actors_from_reports(session, event.id)
        sync_event_knowledge(session, event.id)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_observable_hunt_enrich_promote_and_revoke(
    hunt_campaign_client: TestClient,
) -> None:
    listed = hunt_campaign_client.get(
        "/api/v1/observables?q=interview-example.com&observable_type=domain"
    )
    assert listed.status_code == 200
    observable = listed.json()[0]
    assert observable["indicator"] is None
    assert observable["ai_disposition"] is None
    assert observable["report_count"] == 1
    assert observable["event_count"] == 1

    detail = hunt_campaign_client.get(f"/api/v1/observables/{observable['id']}")
    assert detail.status_code == 200
    assert detail.json()["events"][0]["event_title"] == "Lazarus fake interview campaign"
    evidence_id = detail.json()["reports"][0]["evidence_id"]

    enriched = hunt_campaign_client.post(f"/api/v1/observables/{observable['id']}/enrich")
    assert enriched.status_code == 200
    assert enriched.json()["provider"] == "local-context"
    assert enriched.json()["result"]["external_provider_used"] is False

    now = datetime.now(UTC)
    invalid = hunt_campaign_client.post(
        f"/api/v1/observables/{observable['id']}/promote",
        json={
            "purpose": "Credential phishing infrastructure",
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=30)).isoformat(),
            "confidence": 90,
            "severity": "high",
            "evidence_ids": [str(uuid4())],
        },
    )
    assert invalid.status_code == 422

    promoted = hunt_campaign_client.post(
        f"/api/v1/observables/{observable['id']}/promote",
        json={
            "purpose": "Credential phishing infrastructure",
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=30)).isoformat(),
            "confidence": 90,
            "severity": "high",
            "evidence_ids": [evidence_id],
        },
    )
    assert promoted.status_code == 200
    indicator = promoted.json()
    assert indicator["reviewed_by"] == "local-analyst"
    assert indicator["pattern"] == "[domain-name:value = 'interview-example.com']"
    assert (
        hunt_campaign_client.get("/api/v1/indicators?revoked=false").json()[0]["id"]
        == indicator["id"]
    )
    assert (
        hunt_campaign_client.post(
            f"/api/v1/observables/{observable['id']}/promote",
            json={
                "purpose": "Duplicate",
                "valid_from": now.isoformat(),
                "valid_until": (now + timedelta(days=1)).isoformat(),
                "confidence": 50,
                "severity": "low",
                "evidence_ids": [evidence_id],
            },
        ).status_code
        == 409
    )

    revoked = hunt_campaign_client.patch(
        f"/api/v1/indicators/{indicator['id']}",
        json={"expected_version": indicator["version"], "revoked": True},
    )
    stale = hunt_campaign_client.patch(
        f"/api/v1/indicators/{indicator['id']}",
        json={"expected_version": indicator["version"], "confidence": 20},
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked"] is True
    assert revoked.json()["reviewed_by"] == "local-analyst"
    assert stale.status_code == 409


def test_campaign_membership_requires_human_evidence_and_is_reversible(
    hunt_campaign_client: TestClient,
) -> None:
    event = hunt_campaign_client.get("/api/v1/events").json()[0]
    created = hunt_campaign_client.post(
        "/api/v1/campaigns",
        json={
            "name": "Operation Dream Job",
            "description": "Lazarus recruitment-themed activity.",
            "status": "active",
        },
    )
    assert created.status_code == 201
    campaign = created.json()

    assigned = hunt_campaign_client.post(
        f"/api/v1/campaigns/{campaign['id']}/events",
        json={
            "event_id": event["id"],
            "stage": "initial-access",
            "confidence": 94,
            "evidence_note": "The analyst confirmed the fake interview event belongs here.",
            "expected_version": campaign["version"],
        },
    )
    assert assigned.status_code == 200
    campaign = assigned.json()
    assert campaign["event_count"] == 1
    assert campaign["actor_names"] == ["Lazarus Group"]
    assert campaign["events"][0]["stage"] == "initial-access"
    assert campaign["events"][0]["evidence_note"]
    assert hunt_campaign_client.get("/api/v1/campaigns").json()[0]["stages"] == ["initial-access"]

    watch_rule = hunt_campaign_client.post(
        "/api/v1/watch-rules",
        json={
            "name": "Follow Operation Dream Job",
            "description": "Created directly from the campaign detail.",
            "conditions": {"campaign_ids": [campaign["id"]]},
            "severity": "high",
            "enabled": True,
            "created_by": "analyst",
        },
    )
    assert watch_rule.status_code == 201
    preview = hunt_campaign_client.post(
        f"/api/v1/watch-rules/{watch_rule.json()['id']}/preview"
    )
    assert preview.status_code == 200
    assert preview.json()["match_count"] == 1
    assert preview.json()["matches"][0]["subject_id"] == event["id"]
    assert preview.json()["matches"][0]["matched_on"]["campaign_ids"] == [campaign["id"]]

    removed = hunt_campaign_client.delete(
        f"/api/v1/campaigns/{campaign['id']}/events/{event['id']}"
        f"?expected_version={campaign['version']}"
    )
    assert removed.status_code == 204
    assert (
        hunt_campaign_client.get(f"/api/v1/campaigns/{campaign['id']}").json()["event_count"] == 0
    )
