from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.db.session import get_db
from apt_hunter.main import app
from apt_hunter.models import Report, ReportAnalysis, Source
from apt_hunter.services.knowledge import persist_report_knowledge


@pytest.fixture
def review_client() -> Generator[tuple[TestClient, str], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with testing_session.begin() as session:
        source = Source(type="rss", name="Security Research", url="https://example.org/feed")
        session.add(source)
        session.flush()
        report = Report(
            source_id=source.id,
            title="APT29 launches a phishing campaign",
            canonical_url="https://example.org/report",
            normalized_text="RSS summary",
            exact_hash="b" * 64,
            relevance_score=90,
            relevance_reasons=["actor", "phishing"],
            status="candidate",
            published_at=datetime.now(UTC),
        )
        session.add(report)
        session.flush()
        session.add(
            ReportAnalysis(
                report_id=report.id,
                extraction_status="ready",
                review_status="pending",
                content_text="APT29 sent phishing emails to diplomats. " * 5,
                actors=[
                    {
                        "name": "APT29",
                        "type": "threat-actor",
                        "confidence": 90,
                        "evidence": "APT29 sent phishing emails.",
                    }
                ],
                capabilities=[],
                infrastructure=[],
                victims=[],
                evidence=[],
                confidence_auto=80,
            )
        )
        persist_report_knowledge(
            session,
            report_id=report.id,
            observed_at=report.published_at or report.created_at,
            observables=[
                {
                    "type": "domain",
                    "value": "evil-example.com",
                    "normalized": "evil-example.com",
                    "scope": "public",
                    "confidence": 98,
                    "evidence": "APT29 used evil-example.com for credential phishing.",
                    "start_offset": 18,
                    "end_offset": 34,
                }
            ],
            techniques=[
                {
                    "technique_id": "T1566.001",
                    "name": "MITRE ATT&CK T1566.001",
                    "tactic": None,
                    "confidence": 99,
                    "evidence": "The campaign used spearphishing attachments (T1566.001).",
                    "start_offset": 35,
                    "end_offset": 44,
                }
            ],
            method_version="rules-v2",
        )
        report_id = str(report.id)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, report_id
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_report_detail_and_review_queue(review_client: tuple[TestClient, str]) -> None:
    client, report_id = review_client

    listed = client.get("/api/v1/reports")
    detail = client.get(f"/api/v1/reports/{report_id}")
    queue = client.get("/api/v1/reviews")

    assert listed.status_code == 200
    assert listed.json()[0]["source_name"] == "Security Research"
    assert detail.status_code == 200
    assert detail.json()["analysis"]["actors"][0]["name"] == "APT29"
    assert [item["id"] for item in queue.json()] == [report_id]


def test_report_scope_and_summary_use_database_totals(
    review_client: tuple[TestClient, str],
) -> None:
    client, report_id = review_client

    summary = client.get("/api/v1/reports/summary")
    apt_before_review = client.get("/api/v1/reports?scope=apt")
    raw = client.get("/api/v1/reports?scope=raw")

    assert summary.status_code == 200
    assert summary.json() == {
        "total": 1,
        "apt": 0,
        "pending": 1,
        "excluded": 0,
        "extraction_failed": 0,
    }
    assert apt_before_review.json() == []
    assert [item["id"] for item in raw.json()] == [report_id]

    approved = client.post(
        f"/api/v1/reviews/{report_id}/decision",
        json={
            "decision": "approved",
            "analyst_note": "Human review confirms this is an APT event.",
            "expected_version": 1,
            "actors": [],
            "capabilities": [],
            "infrastructure": [],
            "victims": [],
        },
    )
    assert approved.status_code == 200
    assert [item["id"] for item in client.get("/api/v1/reports?scope=apt").json()] == [report_id]
    assert client.get("/api/v1/reports/summary").json()["apt"] == 1


def test_review_decision_is_versioned(review_client: tuple[TestClient, str]) -> None:
    client, report_id = review_client
    payload = {
        "decision": "approved",
        "analyst_note": "Evidence confirmed.",
        "expected_version": 1,
        "event_title": "APT29 diplomatic phishing campaign",
        "confidence_analyst": 92,
        "actors": [
            {
                "name": "Midnight Blizzard",
                "type": "threat-actor",
                "confidence": 95,
                "evidence": "Analyst normalized APT29 to its preferred name.",
            }
        ],
        "capabilities": [
            {
                "name": "Spearphishing",
                "type": "attack-pattern",
                "confidence": 90,
                "evidence": "The report describes targeted phishing emails.",
            }
        ],
        "infrastructure": [],
        "victims": [],
    }

    approved = client.post(f"/api/v1/reviews/{report_id}/decision", json=payload)
    stale = client.post(f"/api/v1/reviews/{report_id}/decision", json=payload)
    events = client.get("/api/v1/events")
    revisions = client.get(f"/api/v1/reviews/{report_id}/revisions")
    actors = client.get("/api/v1/actors")

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["analysis"]["version"] == 2
    assert approved.json()["analysis"]["reviewed_actors"][0]["name"] == "Midnight Blizzard"
    assert stale.status_code == 409
    assert events.status_code == 200
    assert events.json()[0]["title"] == "APT29 diplomatic phishing campaign"
    assert events.json()[0]["actor_names"] == ["Midnight Blizzard"]
    event_id = events.json()[0]["id"]
    event = client.get(f"/api/v1/events/{event_id}")
    assert event.status_code == 200
    assert event.json()["diamond"]["capabilities"][0]["name"] == "Spearphishing"
    assert event.json()["reports"][0]["id"] == report_id
    assert event.json()["observables"][0]["value_normalized"] == "evil-example.com"
    assert event.json()["observables"][0]["evidence"]
    assert event.json()["attack_techniques"][0]["technique_id"] == "T1566.001"
    assert revisions.status_code == 200
    assert revisions.json()[0]["review_version"] == 2
    assert revisions.json()[0]["snapshot"]["infrastructure"] == []
    assert actors.status_code == 200
    assert actors.json()[0]["canonical_name"] == "Midnight Blizzard"
    assert "APT29" in actors.json()[0]["aliases"]
    assert actors.json()[0]["event_count"] == 1
    actor_id = actors.json()[0]["id"]
    actor = client.get(f"/api/v1/actors/{actor_id}?granularity=year")
    assert actor.status_code == 200
    assert actor.json()["events"][0]["id"] == event_id
    assert actor.json()["timeline"][0]["event_count"] == 1
    assert client.get("/api/v1/actors?date_from=2099-01-01").json() == []


def test_rejected_review_does_not_create_event(review_client: tuple[TestClient, str]) -> None:
    client, report_id = review_client

    rejected = client.post(
        f"/api/v1/reviews/{report_id}/decision",
        json={
            "decision": "rejected",
            "analyst_note": "The article does not contain enough attribution evidence.",
            "expected_version": 1,
            "actors": [],
            "capabilities": [],
            "infrastructure": [],
            "victims": [],
        },
    )

    assert rejected.status_code == 200
    assert rejected.json()["analysis"]["reviewed_actors"] == []
    assert client.get("/api/v1/events").json() == []
    assert client.get("/api/v1/actors").json() == []


def test_actor_tracking_comparison_summary_and_export(
    review_client: tuple[TestClient, str],
) -> None:
    client, report_id = review_client
    approved = client.post(
        f"/api/v1/reviews/{report_id}/decision",
        json={
            "decision": "approved",
            "analyst_note": "Tracking evidence confirmed.",
            "expected_version": 1,
            "event_title": "APT29 fake interview operation",
            "confidence_analyst": 93,
            "actors": [
                {
                    "name": "Midnight Blizzard",
                    "type": "threat-actor",
                    "confidence": 95,
                    "evidence": "APT29 attribution confirmed.",
                }
            ],
            "capabilities": [
                {
                    "name": "Fake Interview Loader",
                    "type": "malware",
                    "confidence": 90,
                    "evidence": "The loader was delivered during interviews.",
                }
            ],
            "infrastructure": [
                {
                    "name": "evil-example.com",
                    "type": "domain",
                    "confidence": 95,
                    "evidence": "The domain hosted credential phishing.",
                }
            ],
            "victims": [
                {
                    "name": "Diplomatic organizations",
                    "type": "sector",
                    "confidence": 88,
                    "evidence": "Diplomatic organizations were targeted.",
                }
            ],
        },
    )
    assert approved.status_code == 200
    actor_id = client.get("/api/v1/actors").json()[0]["id"]
    today = date.today()
    date_from = today - timedelta(days=1)
    query = f"date_from={date_from.isoformat()}&date_to={today.isoformat()}"

    tracking = client.get(f"/api/v1/actors/{actor_id}/tracking?{query}")
    assert tracking.status_code == 200
    payload = tracking.json()
    assert payload["period"]["bucket"] == "day"
    assert payload["period"]["day_count"] == 2
    assert payload["comparison"] == {
        "current_event_count": 1,
        "previous_event_count": 0,
        "absolute_change": 1,
        "percentage_change": None,
    }
    changes = {item["category"]: item for item in payload["changes"]}
    assert changes["malware"]["new_values"] == ["Fake Interview Loader"]
    assert changes["infrastructure"]["new_values"] == ["evil-example.com"]
    assert changes["targets"]["new_values"] == ["Diplomatic organizations"]
    assert changes["techniques"]["new_values"][0].startswith("T1566.001")

    summary = client.post(f"/api/v1/actors/{actor_id}/tracking/summary?{query}")
    assert summary.status_code == 200
    assert summary.json()["status"] == "draft"
    assert summary.json()["supporting_event_ids"] == [payload["events"][0]["id"]]
    assert summary.json()["supporting_evidence_ids"]
    assert "分析员" in summary.json()["caveats"][2]

    json_export = client.get(f"/api/v1/actors/{actor_id}/tracking/export?{query}&format=json")
    csv_export = client.get(f"/api/v1/actors/{actor_id}/tracking/export?{query}&format=csv")
    assert json_export.status_code == 200
    assert "attachment" in json_export.headers["content-disposition"]
    assert csv_export.status_code == 200
    assert "record_type" in csv_export.text
    assert "Fake Interview Loader" in csv_export.text
    assert (
        client.get(
            f"/api/v1/actors/{actor_id}/tracking?date_from=2026-08-02&date_to=2026-08-01"
        ).status_code
        == 422
    )


def test_watch_rule_auto_hit_notification_and_global_search(
    review_client: tuple[TestClient, str],
) -> None:
    client, report_id = review_client
    rule = client.post(
        "/api/v1/watch-rules",
        json={
            "name": "APT29 high-confidence phishing",
            "description": "Track confirmed APT29 phishing events.",
            "conditions": {
                "keywords": ["phishing"],
                "actor_names": ["APT29"],
                "observable_types": ["domain"],
                "technique_ids": ["T1566.001"],
                "min_confidence": 90,
            },
            "severity": "high",
            "enabled": True,
            "created_by": "analyst",
        },
    )
    assert rule.status_code == 201
    rule_id = rule.json()["id"]
    assert client.post(f"/api/v1/watch-rules/{rule_id}/preview").json()["match_count"] == 0

    approved = client.post(
        f"/api/v1/reviews/{report_id}/decision",
        json={
            "decision": "approved",
            "analyst_note": "Attribution and infrastructure confirmed.",
            "expected_version": 1,
            "event_title": "APT29 credential phishing operation",
            "confidence_analyst": 92,
            "actors": [
                {
                    "name": "APT29",
                    "type": "threat-actor",
                    "confidence": 95,
                    "evidence": "APT29 sent phishing emails.",
                }
            ],
            "capabilities": [],
            "infrastructure": [],
            "victims": [],
        },
    )
    assert approved.status_code == 200
    hits = client.get(f"/api/v1/watch-rules/{rule_id}/hits")
    assert hits.status_code == 200
    assert hits.json()[0]["subject_title"] == "APT29 credential phishing operation"
    assert hits.json()[0]["matched_on"]["technique_ids"] == ["T1566.001"]
    evaluated = client.post(f"/api/v1/watch-rules/{rule_id}/evaluate")
    assert evaluated.json()["created_hit_count"] == 0
    assert evaluated.json()["hit_count"] == 1

    notifications = client.get("/api/v1/notifications")
    assert notifications.json()["unread_count"] == 1
    notification_id = notifications.json()["items"][0]["id"]
    assert client.patch(f"/api/v1/notifications/{notification_id}/read").status_code == 200
    assert client.get("/api/v1/notifications").json()["unread_count"] == 0

    actor_search = client.get("/api/v1/search?q=APT29")
    observable_search = client.get("/api/v1/search?q=evil-example.com")
    report_search = client.get("/api/v1/search?q=phishing")
    assert actor_search.status_code == 200
    assert any(item["kind"] == "actor" for item in actor_search.json()["results"])
    assert any(item["kind"] == "observable" for item in observable_search.json()["results"])
    assert any(item["kind"] == "report" for item in report_search.json()["results"])


def test_persistent_job_cancel_and_retry(
    review_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, report_id = review_client
    monkeypatch.setattr("apt_hunter.api.routes.reports.dispatch_job", lambda _: None)
    monkeypatch.setattr("apt_hunter.api.routes.operations.dispatch_job", lambda _: None)
    monkeypatch.setattr(
        "apt_hunter.api.routes.operations.celery_app.control.revoke",
        lambda *_args, **_kwargs: None,
    )

    queued = client.post(f"/api/v1/reports/{report_id}/enrich")
    assert queued.status_code == 202
    jobs = client.get("/api/v1/operations/jobs")
    assert jobs.status_code == 200
    job = jobs.json()[0]
    assert job["task_id"] == queued.json()["task_id"]
    assert job["status"] == "queued"
    assert job["subject_id"] == report_id

    canceled = client.post(
        f"/api/v1/operations/jobs/{job['id']}/cancel?expected_version={job['version']}"
    )
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    retried = client.post(f"/api/v1/operations/jobs/{job['id']}/retry")
    assert retried.status_code == 202
    assert retried.json()["attempt"] == 2
    assert retried.json()["parent_job_id"] == job["id"]
