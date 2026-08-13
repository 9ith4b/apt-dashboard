from apt_hunter.services.ai_gateway import (
    AIAnalysisPayload,
    AIVerificationPayload,
    _normalize_analysis_payload,
    _normalize_verification_payload,
)


def test_normalize_analysis_payload_accepts_common_model_variants() -> None:
    payload = _normalize_analysis_payload(
        {
            "result": {
                "relevant": True,
                "relevance_score": 0.95,
                "classification": "apt_event",
                "summary": "An evidence-backed APT report.",
                "confidence": "92%",
                "actors": [
                    {
                        "name": "APT Example",
                        "confidence": 0.9,
                        "evidence": "APT Example targeted users.",
                    }
                ],
                "capabilities": [
                    {
                        "name": "Credential theft",
                        "evidence": "The actor stole credentials.",
                    }
                ],
                "observables": [
                    {
                        "type": "domain",
                        "normalized": "interview-example.com",
                        "disposition": "malicious",
                        "role": "payload delivery",
                        "confidence": "96%",
                        "indicator_candidate": True,
                        "purpose": "Malware delivery infrastructure",
                        "severity": "high",
                        "ttl_days": 30,
                        "evidence": "interview-example.com delivered the payload.",
                        "decision_reason": "The report explicitly describes delivery.",
                    }
                ],
                "contradictions": [{"contradiction": "No contradiction found."}],
                "decision_reason": "The report contains quoted evidence.",
            }
        }
    )

    result = AIAnalysisPayload.model_validate(payload)
    assert result.relevance_score == 95
    assert result.confidence == 92
    assert result.actors[0].confidence == 90
    assert result.capabilities[0].type == "capability"
    assert result.observables[0].disposition == "malicious"
    assert result.observables[0].confidence == 96
    assert result.contradictions == ["No contradiction found."]


def test_normalize_verification_payload_converts_fractional_scores() -> None:
    result = AIVerificationPayload.model_validate(
        _normalize_verification_payload(
            {
                "approved": True,
                "confidence": 0.85,
                "evidence_coverage": 0.95,
                "issues": [],
                "contradiction_found": False,
                "decision_reason": "Evidence is sufficient.",
            }
        )
    )
    assert result.confidence == 85
    assert result.evidence_coverage == 95
