from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.config import get_settings
from apt_hunter.db.base import Base
from apt_hunter.models import (
    AIProcessingPolicy,
    Indicator,
    ObservableEnrichment,
    Report,
    Source,
)
from apt_hunter.services.ai_gateway import AIAnalysisPayload, ground_analysis
from apt_hunter.services.automation import _fallback_outcome
from apt_hunter.services.indicator_automation import apply_ai_observable_decisions
from apt_hunter.services.knowledge import persist_report_knowledge
from apt_hunter.services.secrets import decrypt_secret, encrypt_secret


def test_model_credentials_are_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "APT_HUNTER_AI_SECRETS_KEY", "test-secret-key-with-more-than-thirty-two-characters"
    )
    get_settings.cache_clear()

    encrypted = encrypt_secret("sk-sensitive-value")

    assert "sk-sensitive-value" not in encrypted
    assert decrypt_secret(encrypted) == "sk-sensitive-value"
    get_settings.cache_clear()


def test_ai_grounding_rejects_entities_without_source_evidence() -> None:
    payload = AIAnalysisPayload.model_validate(
        {
            "relevant": True,
            "relevance_score": 94,
            "classification": "apt_event",
            "summary": "Lazarus targeted developers with fake interviews.",
            "confidence": 91,
            "actors": [
                {
                    "name": "Lazarus Group",
                    "type": "threat-actor",
                    "confidence": 95,
                    "evidence": "Lazarus Group used fake interviews against developers.",
                },
                {
                    "name": "APT28",
                    "type": "threat-actor",
                    "confidence": 72,
                    "evidence": "APT28 was confirmed by three intelligence agencies.",
                },
            ],
            "claims": [],
            "capabilities": [],
            "infrastructure": [],
            "victims": [],
            "attack_techniques": [],
            "observables": [
                {
                    "type": "domain",
                    "normalized": "interview-example.com",
                    "disposition": "malicious",
                    "role": "payload delivery",
                    "confidence": 96,
                    "indicator_candidate": True,
                    "purpose": "Malware delivery infrastructure",
                    "severity": "high",
                    "ttl_days": 30,
                    "evidence": "interview-example.com delivered malware.",
                    "decision_reason": "The report explicitly describes malware delivery.",
                }
            ],
            "contradictions": [],
            "decision_reason": "The report explicitly identifies Lazarus.",
        }
    )

    grounded, coverage, rejected = ground_analysis(
        payload,
        "Lazarus Group used fake interviews against developers. "
        "interview-example.com delivered malware.",
        [{"type": "domain", "normalized": "interview-example.com"}],
    )

    assert [actor.name for actor in grounded.actors] == ["Lazarus Group"]
    assert [item.normalized for item in grounded.observables] == ["interview-example.com"]
    assert coverage == 67
    assert rejected == ["threat-actor:APT28"]


def test_ai_promotes_grounded_indicator_and_respects_human_override() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    observed_at = datetime(2026, 8, 13, 8, tzinfo=UTC)
    with testing_session.begin() as session:
        source = Source(type="rss", name="Vendor", url="https://vendor.example/feed")
        session.add(source)
        session.flush()
        report = Report(
            source_id=source.id,
            title="Malicious interview infrastructure",
            canonical_url="https://vendor.example/report",
            normalized_text="interview-example.com delivered malware.",
            exact_hash="9" * 64,
            relevance_score=95,
            relevance_reasons=["infrastructure"],
            status="approved",
            published_at=observed_at,
        )
        policy = AIProcessingPolicy(
            key="default",
            automation_enabled=True,
            unattended_mode=True,
            auto_manage_indicators=True,
            indicator_auto_threshold=80,
        )
        session.add_all([report, policy])
        session.flush()
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
                    "confidence": 96,
                    "evidence": "interview-example.com delivered malware.",
                    "start_offset": 0,
                    "end_offset": 21,
                }
            ],
            techniques=[],
            method_version="ai:apt-analysis-v3",
        )
        candidate = {
            "type": "domain",
            "normalized": "interview-example.com",
            "ai_disposition": "malicious",
            "ai_role": "payload delivery",
            "ai_confidence": 96,
            "indicator_candidate": True,
            "indicator_purpose": "Malware delivery infrastructure",
            "indicator_severity": "high",
            "indicator_ttl_days": 30,
            "ai_decision_reason": "The report explicitly describes delivery.",
            "evidence": "interview-example.com delivered malware.",
        }
        result = apply_ai_observable_decisions(
            session, report=report, candidates=[candidate], policy=policy
        )
        session.flush()
        indicator = session.scalar(select(Indicator))
        enrichment = session.scalar(
            select(ObservableEnrichment).where(ObservableEnrichment.provider == "ai-context")
        )
        assert result["promoted"] == 1
        assert indicator is not None
        assert indicator.reviewed_by == "ai-automation"
        assert enrichment is not None
        assert enrichment.result["disposition"] == "malicious"

        indicator.reviewed_by = "analyst"
        indicator.confidence = 42
        apply_ai_observable_decisions(
            session,
            report=report,
            candidates=[{**candidate, "ai_confidence": 100}],
            policy=policy,
        )
        assert indicator.confidence == 42
        assert indicator.reviewed_by == "analyst"

    Base.metadata.drop_all(engine)


def test_unattended_fallback_continues_without_human_gate() -> None:
    deterministic = SimpleNamespace(
        actors=[{"name": "APT Example"}],
        capabilities=[],
        infrastructure=[],
        victims=[],
        attack_techniques=[],
        observables=[],
        confidence=88,
    )
    outcome = _fallback_outcome(
        deterministic=deterministic,
        policy_values={"unattended_mode": True, "relevance_threshold": 60},
        initial_relevance_score=70,
        model_config_id=None,
        exception_type="ai_processing_failed",
        exception_title="AI failed",
        exception_description="timeout",
    )

    assert outcome.automation_status == "fallback"
    assert outcome.review_status == "approved"
    assert outcome.report_status == "approved"
