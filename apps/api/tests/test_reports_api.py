from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.db.session import get_db
from apt_hunter.main import app
from apt_hunter.models import Report, ReportAnalysis, Source


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
