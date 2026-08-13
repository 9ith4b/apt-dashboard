import json
import re
import time
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from apt_hunter.models import AIModelConfig
from apt_hunter.services.secrets import decrypt_secret

PROMPT_VERSION = "apt-analysis-v3"
VERIFY_PROMPT_VERSION = "apt-verifier-v3"


class AIEntity(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    type: str = Field(min_length=1, max_length=100)
    confidence: int = Field(ge=0, le=100)
    evidence: str = Field(min_length=1, max_length=5000)


class AITechnique(BaseModel):
    technique_id: str = Field(pattern=r"^T\d{4}(?:\.\d{3})?$")
    name: str = Field(min_length=1, max_length=200)
    tactic: str | None = Field(default=None, max_length=100)
    confidence: int = Field(ge=0, le=100)
    evidence: str = Field(min_length=1, max_length=5000)


class AIClaim(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    predicate: str = Field(min_length=1, max_length=200)
    object: str = Field(min_length=1, max_length=1000)
    statement_type: Literal["fact", "source_claim", "inference"]
    confidence: int = Field(ge=0, le=100)
    evidence: str = Field(min_length=1, max_length=5000)


class AIObservableAssessment(BaseModel):
    type: str = Field(min_length=1, max_length=32)
    normalized: str = Field(min_length=1, max_length=4000)
    disposition: Literal["malicious", "suspicious", "benign", "context"]
    role: str = Field(min_length=1, max_length=200)
    confidence: int = Field(ge=0, le=100)
    indicator_candidate: bool
    purpose: str = Field(default="", max_length=500)
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    ttl_days: int = Field(default=30, ge=1, le=365)
    evidence: str = Field(min_length=1, max_length=5000)
    decision_reason: str = Field(min_length=1, max_length=2000)


class AIAnalysisPayload(BaseModel):
    relevant: bool
    relevance_score: int = Field(ge=0, le=100)
    classification: Literal[
        "apt_event",
        "malware_analysis",
        "vulnerability_activity",
        "actor_research",
        "security_news",
        "irrelevant",
    ]
    summary: str = Field(max_length=3000)
    confidence: int = Field(ge=0, le=100)
    actors: list[AIEntity] = Field(default_factory=list)
    capabilities: list[AIEntity] = Field(default_factory=list)
    infrastructure: list[AIEntity] = Field(default_factory=list)
    victims: list[AIEntity] = Field(default_factory=list)
    attack_techniques: list[AITechnique] = Field(default_factory=list)
    observables: list[AIObservableAssessment] = Field(default_factory=list)
    claims: list[AIClaim] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    decision_reason: str = Field(max_length=3000)


class AIVerificationPayload(BaseModel):
    approved: bool
    confidence: int = Field(ge=0, le=100)
    evidence_coverage: int = Field(ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    contradiction_found: bool = False
    decision_reason: str = Field(max_length=3000)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    payload: dict[str, object]
    latency_ms: int


def _json_from_content(content: str) -> dict[str, object]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Model did not return a JSON object")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value


_CLASSIFICATIONS = {
    "apt_event",
    "malware_analysis",
    "vulnerability_activity",
    "actor_research",
    "security_news",
    "irrelevant",
}


def _unwrap_payload(payload: dict[str, object]) -> dict[str, object]:
    """Accept common OpenAI-compatible wrappers without weakening the contract."""
    current = payload
    for _ in range(2):
        nested = None
        for key in ("result", "analysis", "data", "output"):
            value = current.get(key)
            if isinstance(value, dict) and not any(
                field in current
                for field in ("relevant", "approved", "classification", "summary")
            ):
                nested = value
                break
        if nested is None:
            return current
        current = nested
    return current


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return " ".join(item for item in (_text(item) for item in value) if item)
    return ""


def _clip(value: object, limit: int) -> str:
    return _text(value)[:limit]


def _score(value: object, default: int = 0) -> int:
    """Normalize model scores expressed as integers, percentages, or 0..1 floats."""
    if isinstance(value, bool):
        return default
    raw = _text(value)
    if raw.endswith("%"):
        raw = raw[:-1].strip()
        try:
            return max(0, min(100, round(float(raw))))
        except ValueError:
            return default
    try:
        number = float(value) if isinstance(value, (int, float)) else float(raw)
    except (TypeError, ValueError):
        return default
    if 0 <= number <= 1:
        number *= 100
    return max(0, min(100, round(number)))


def _boolean(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    normalized = _text(value).casefold()
    if normalized in {"true", "yes", "1", "是", "通过", "approved"}:
        return True
    if normalized in {"false", "no", "0", "否", "拒绝", "rejected"}:
        return False
    return default


def _items(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _entity_items(value: object, dimension: str) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in _items(value):
        if not isinstance(item, dict):
            continue
        name = _clip(item.get("name") or item.get("entity") or item.get("value"), 500)
        evidence = _clip(
            item.get("evidence")
            or item.get("quote")
            or item.get("excerpt")
            or item.get("context"),
            5000,
        )
        # An entity without a quote cannot pass grounding, so discard only that
        # malformed item instead of failing the entire article analysis.
        if not name or not evidence:
            continue
        normalized.append(
            {
                "name": name,
                "type": _clip(item.get("type") or dimension, 100),
                "confidence": _score(item.get("confidence"), 0),
                "evidence": evidence,
            }
        )
    return normalized


def _technique_items(value: object) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in _items(value):
        if not isinstance(item, dict):
            continue
        technique_id = _clip(
            item.get("technique_id") or item.get("id") or item.get("technique"), 32
        ).upper()
        if not re.fullmatch(r"T\d{4}(?:\.\d{3})?", technique_id):
            continue
        name = _clip(item.get("name") or item.get("technique_name"), 200)
        evidence = _clip(
            item.get("evidence")
            or item.get("quote")
            or item.get("excerpt")
            or item.get("context"),
            5000,
        )
        if not name or not evidence:
            continue
        normalized.append(
            {
                "technique_id": technique_id,
                "name": name,
                "tactic": _clip(item.get("tactic"), 100) or None,
                "confidence": _score(item.get("confidence"), 0),
                "evidence": evidence,
            }
        )
    return normalized


def _claim_items(value: object) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in _items(value):
        if not isinstance(item, dict):
            continue
        subject = _clip(item.get("subject") or item.get("entity"), 500)
        predicate = _clip(item.get("predicate") or item.get("relation"), 200)
        object_value = _clip(item.get("object") or item.get("value"), 1000)
        evidence = _clip(
            item.get("evidence")
            or item.get("quote")
            or item.get("excerpt")
            or item.get("context"),
            5000,
        )
        if not subject or not predicate or not object_value or not evidence:
            continue
        statement_type = _text(item.get("statement_type") or item.get("type")).casefold()
        if statement_type not in {"fact", "source_claim", "inference"}:
            statement_type = "inference"
        normalized.append(
            {
                "subject": subject,
                "predicate": predicate,
                "object": object_value,
                "statement_type": statement_type,
                "confidence": _score(item.get("confidence"), 0),
                "evidence": evidence,
            }
        )
    return normalized


def _observable_items(value: object) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    allowed_dispositions = {"malicious", "suspicious", "benign", "context"}
    allowed_severities = {"info", "low", "medium", "high", "critical"}
    for item in _items(value):
        if not isinstance(item, dict):
            continue
        observable_type = _clip(item.get("type") or item.get("observable_type"), 32).casefold()
        value_normalized = _clip(
            item.get("normalized") or item.get("value_normalized") or item.get("value"),
            4000,
        )
        evidence = _clip(
            item.get("evidence")
            or item.get("quote")
            or item.get("excerpt")
            or item.get("context"),
            5000,
        )
        disposition = _text(item.get("disposition") or item.get("verdict")).casefold()
        aliases = {
            "indicator": "malicious",
            "malware": "malicious",
            "unknown": "context",
            "observable": "context",
            "legitimate": "benign",
            "恶意": "malicious",
            "可疑": "suspicious",
            "良性": "benign",
            "上下文": "context",
        }
        disposition = aliases.get(disposition, disposition)
        if (
            not observable_type
            or not value_normalized
            or not evidence
            or disposition not in allowed_dispositions
        ):
            continue
        severity = _text(item.get("severity")).casefold()
        if severity not in allowed_severities:
            severity = "high" if disposition == "malicious" else "info"
        ttl_value = item.get("ttl_days", 30)
        try:
            ttl_days = max(1, min(365, int(float(str(ttl_value)))))
        except (TypeError, ValueError):
            ttl_days = 30
        role = _clip(item.get("role") or item.get("purpose") or disposition, 200)
        purpose = _clip(item.get("purpose") or item.get("malicious_purpose"), 500)
        decision_reason = _clip(
            item.get("decision_reason") or item.get("reason") or evidence,
            2000,
        )
        indicator_candidate = _boolean(
            item.get("indicator_candidate"), disposition == "malicious"
        )
        normalized.append(
            {
                "type": observable_type,
                "normalized": value_normalized,
                "disposition": disposition,
                "role": role,
                "confidence": _score(item.get("confidence"), 0),
                "indicator_candidate": indicator_candidate,
                "purpose": purpose,
                "severity": severity,
                "ttl_days": ttl_days,
                "evidence": evidence,
                "decision_reason": decision_reason,
            }
        )
    return normalized


def _string_items(value: object) -> list[str]:
    values: list[str] = []
    for item in _items(value):
        if isinstance(item, dict):
            item = item.get("contradiction") or item.get("issue") or item.get("reason")
        text = _clip(item, 3000)
        if text:
            values.append(text)
    return values


def _normalize_classification(value: object) -> str:
    normalized = _text(value).casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "apt": "apt_event",
        "apt_activity": "apt_event",
        "apt事件": "apt_event",
        "恶意软件": "malware_analysis",
        "漏洞": "vulnerability_activity",
        "漏洞活动": "vulnerability_activity",
        "组织研究": "actor_research",
        "安全新闻": "security_news",
        "无关": "irrelevant",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in _CLASSIFICATIONS:
        raise ValueError(f"Unsupported AI classification: {value!r}")
    return normalized


def _normalize_analysis_payload(payload: dict[str, object]) -> dict[str, object]:
    raw = _unwrap_payload(payload)
    relevance_score = _score(raw.get("relevance_score", raw.get("relevance")), 0)
    classification = _normalize_classification(raw.get("classification"))
    return {
        "relevant": _boolean(raw.get("relevant", raw.get("is_relevant")), relevance_score >= 60),
        "relevance_score": relevance_score,
        "classification": classification,
        "summary": _clip(raw.get("summary") or raw.get("abstract"), 3000),
        "confidence": _score(raw.get("confidence", raw.get("confidence_score")), 0),
        "actors": _entity_items(raw.get("actors"), "actor"),
        "capabilities": _entity_items(raw.get("capabilities"), "capability"),
        "infrastructure": _entity_items(raw.get("infrastructure"), "infrastructure"),
        "victims": _entity_items(raw.get("victims"), "victim"),
        "attack_techniques": _technique_items(raw.get("attack_techniques")),
        "observables": _observable_items(
            raw.get("observables") or raw.get("observable_assessments")
        ),
        "claims": _claim_items(raw.get("claims")),
        "contradictions": _string_items(raw.get("contradictions")),
        "decision_reason": _clip(raw.get("decision_reason") or raw.get("reason"), 3000),
    }


def _normalize_verification_payload(payload: dict[str, object]) -> dict[str, object]:
    raw = _unwrap_payload(payload)
    return {
        "approved": _boolean(raw.get("approved", raw.get("is_approved"))),
        "confidence": _score(raw.get("confidence", raw.get("confidence_score")), 0),
        "evidence_coverage": _score(
            raw.get("evidence_coverage", raw.get("evidenceCoverage")), 0
        ),
        "issues": _string_items(raw.get("issues")),
        "contradiction_found": _boolean(
            raw.get("contradiction_found", raw.get("contradiction"))
        ),
        "decision_reason": _clip(raw.get("decision_reason") or raw.get("reason"), 3000),
    }


def _chat(
    config: AIModelConfig,
    messages: list[dict[str, str]],
    *,
    json_mode: bool = True,
) -> ModelResponse:
    endpoint = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = decrypt_secret(config.api_key_ciphertext)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body: dict[str, object] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    started = time.perf_counter()
    with httpx.Client(timeout=config.timeout_seconds, follow_redirects=False) as client:
        response = client.post(endpoint, headers=headers, json=body)
        if response.status_code == 400 and json_mode:
            body.pop("response_format", None)
            response = client.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
    latency_ms = round((time.perf_counter() - started) * 1000)
    payload = response.json()
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError("Model response did not contain choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ValueError("Model response did not contain textual content")
    return ModelResponse(payload=_json_from_content(content), latency_ms=latency_ms)


def analyze_with_model(
    config: AIModelConfig,
    *,
    title: str,
    content: str,
    observables: list[dict[str, object]] | None = None,
) -> tuple[AIAnalysisPayload, int]:
    system = """你是APT威胁情报分析员。分析输入报告并只返回一个JSON对象。禁止补充原文没有的信息。
每个实体、ATT&CK技术和主张都必须提供原文中的逐字证据片段；无法引用原文的项目必须省略。
严格区分：fact=可直接观察事实；source_claim=来源明确提出的归因或判断；inference=你的推断。
归因措辞如疑似、可能、关联不得改写为确认。组织别名只能在上下文明示或有充分证据时关联。
所有 confidence 和 relevance_score 都必须是0到100的整数，不得使用0到1的小数或百分比字符串。
实体必须是对象数组，每项包含name,type,confidence,evidence；能力也必须使用同样的对象格式。
ATT&CK字段为technique_id,name,tactic,confidence,evidence；主张字段为subject,predicate,object,
statement_type,confidence,evidence；contradictions必须是字符串数组。
对候选技术对象逐一结合上下文判断，而不是因为格式匹配就判恶意。observables数组每项必须包含：
type,normalized,disposition,role,confidence,indicator_candidate,purpose,severity,ttl_days,
evidence,decision_reason。normalized必须原样复制候选对象；disposition只能是malicious、suspicious、
benign、context。只有原文明确将对象用作攻击基础设施、恶意载荷或检测特征时才能设为malicious和
indicator_candidate=true；受害者地址、作者邮箱、合法品牌、报告链接和共享基础设施通常是context或benign。
输出字段：relevant,relevance_score,classification,summary,confidence,actors,capabilities,
infrastructure,victims,attack_techniques,observables,claims,contradictions,decision_reason。
classification只能是apt_event、malware_analysis、vulnerability_activity、actor_research、
security_news、irrelevant。"""
    candidates = [
        {
            "type": item.get("type"),
            "normalized": item.get("normalized"),
            "evidence": item.get("evidence"),
        }
        for item in (observables or [])[:200]
    ]
    user = (
        f"报告标题：{title}\n\n候选技术对象（仅可评估这些对象）：\n"
        f"{json.dumps(candidates, ensure_ascii=False)}\n\n报告正文：\n{content}"
    )
    response = _chat(
        config,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return (
        AIAnalysisPayload.model_validate(_normalize_analysis_payload(response.payload)),
        response.latency_ms,
    )


def verify_with_model(
    config: AIModelConfig,
    *,
    title: str,
    content: str,
    analysis: AIAnalysisPayload,
) -> tuple[AIVerificationPayload, int]:
    system = """你是独立的APT情报质量验证员。只返回一个JSON对象，不重新生成报告。
逐项检查分析结论是否有原文证据、是否混淆事实/来源主张/推断、是否过度归因、
是否存在实体混淆或ATT&CK过度映射。evidence_coverage表示有效证据覆盖比例。
confidence和evidence_coverage必须输出0到100的整数，不得输出0到1的小数。
issues必须是字符串数组。输出字段：approved,confidence,evidence_coverage,issues,
contradiction_found,decision_reason。"""
    user = f"标题：{title}\n\n原文：\n{content}\n\n待验证分析：\n{analysis.model_dump_json()}"
    response = _chat(
        config,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return (
        AIVerificationPayload.model_validate(_normalize_verification_payload(response.payload)),
        response.latency_ms,
    )


def test_model_connection(config: AIModelConfig) -> tuple[int, str]:
    response = _chat(
        config,
        [
            {
                "role": "system",
                "content": "只返回JSON对象，字段ok必须为true，message为简短中文。",
            },
            {"role": "user", "content": "回复连接测试结果。"},
        ],
    )
    if response.payload.get("ok") is not True:
        raise ValueError("Model responded but did not pass the connection contract")
    return response.latency_ms, str(response.payload.get("message", "连接成功"))


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def evidence_is_grounded(evidence: str, content: str) -> bool:
    quote = _normalized(evidence)
    return len(quote) >= 8 and quote in _normalized(content)


def ground_analysis(
    analysis: AIAnalysisPayload,
    content: str,
    observable_candidates: list[dict[str, object]] | None = None,
) -> tuple[AIAnalysisPayload, int, list[str]]:
    rejected: list[str] = []
    total = 0
    grounded = 0

    def entities(values: list[AIEntity]) -> list[AIEntity]:
        nonlocal total, grounded
        accepted: list[AIEntity] = []
        for value in values:
            total += 1
            if evidence_is_grounded(value.evidence, content):
                grounded += 1
                accepted.append(value)
            else:
                rejected.append(f"{value.type}:{value.name}")
        return accepted

    techniques: list[AITechnique] = []
    for technique in analysis.attack_techniques:
        total += 1
        if evidence_is_grounded(technique.evidence, content):
            grounded += 1
            techniques.append(technique)
        else:
            rejected.append(f"attack-technique:{technique.technique_id}")

    claims: list[AIClaim] = []
    for claim in analysis.claims:
        total += 1
        if evidence_is_grounded(claim.evidence, content):
            grounded += 1
            claims.append(claim)
        else:
            rejected.append(f"claim:{claim.subject}:{claim.predicate}")

    candidate_keys = {
        (str(item.get("type", "")).casefold(), str(item.get("normalized", "")))
        for item in (observable_candidates or [])
    }
    observables: list[AIObservableAssessment] = []
    for observable in analysis.observables:
        total += 1
        key = (observable.type.casefold(), observable.normalized)
        if evidence_is_grounded(observable.evidence, content) and key in candidate_keys:
            grounded += 1
            observables.append(observable)
        else:
            rejected.append(f"observable:{observable.type}:{observable.normalized}")

    grounded_analysis = analysis.model_copy(
        update={
            "actors": entities(analysis.actors),
            "capabilities": entities(analysis.capabilities),
            "infrastructure": entities(analysis.infrastructure),
            "victims": entities(analysis.victims),
            "attack_techniques": techniques,
            "observables": observables,
            "claims": claims,
        }
    )
    coverage = 100 if total == 0 else round(grounded * 100 / total)
    return grounded_analysis, coverage, rejected
