import pytest

from apt_hunter.config import get_settings
from apt_hunter.services.ai_gateway import AIAnalysisPayload, ground_analysis
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
            "contradictions": [],
            "decision_reason": "The report explicitly identifies Lazarus.",
        }
    )

    grounded, coverage, rejected = ground_analysis(
        payload,
        "Lazarus Group used fake interviews against developers.",
    )

    assert [actor.name for actor in grounded.actors] == ["Lazarus Group"]
    assert coverage == 50
    assert rejected == ["threat-actor:APT28"]
