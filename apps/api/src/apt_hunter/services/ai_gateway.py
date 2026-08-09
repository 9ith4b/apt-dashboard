import json
import re
import time
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from apt_hunter.models import AIModelConfig
from apt_hunter.services.secrets import decrypt_secret

PROMPT_VERSION = "apt-analysis-v1"
VERIFY_PROMPT_VERSION = "apt-verifier-v1"


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
) -> tuple[AIAnalysisPayload, int]:
    system = """你是APT威胁情报分析员。分析输入报告并只返回JSON。禁止补充原文没有的信息。
每个实体、ATT&CK技术和主张都必须提供原文中的逐字证据片段。严格区分：
fact=可直接观察事实；source_claim=来源明确提出的归因或判断；inference=你的推断。
归因措辞如疑似、可能、关联不得改写为确认。组织别名只能在上下文明示或有充分证据时关联。
输出字段：relevant,relevance_score,classification,summary,confidence,actors,capabilities,
infrastructure,victims,attack_techniques,claims,contradictions,decision_reason。
classification只能是apt_event、malware_analysis、vulnerability_activity、actor_research、
security_news、irrelevant。实体字段为name,type,confidence,evidence；ATT&CK字段为
technique_id,name,tactic,confidence,evidence；主张字段为subject,predicate,object,
statement_type,confidence,evidence。所有分数范围0到100。"""
    user = f"报告标题：{title}\n\n报告正文：\n{content}"
    response = _chat(
        config,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return AIAnalysisPayload.model_validate(response.payload), response.latency_ms


def verify_with_model(
    config: AIModelConfig,
    *,
    title: str,
    content: str,
    analysis: AIAnalysisPayload,
) -> tuple[AIVerificationPayload, int]:
    system = """你是独立的APT情报质量验证员。只返回JSON，不重新生成报告。
逐项检查分析结论是否有原文证据、是否混淆事实/来源主张/推断、是否过度归因、
是否存在实体混淆或ATT&CK过度映射。evidence_coverage表示有效证据覆盖比例。
输出字段：approved,confidence,evidence_coverage,issues,contradiction_found,decision_reason。"""
    user = f"标题：{title}\n\n原文：\n{content}\n\n待验证分析：\n{analysis.model_dump_json()}"
    response = _chat(
        config,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return AIVerificationPayload.model_validate(response.payload), response.latency_ms


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

    grounded_analysis = analysis.model_copy(
        update={
            "actors": entities(analysis.actors),
            "capabilities": entities(analysis.capabilities),
            "infrastructure": entities(analysis.infrastructure),
            "victims": entities(analysis.victims),
            "attack_techniques": techniques,
            "claims": claims,
        }
    )
    coverage = 100 if total == 0 else round(grounded * 100 / total)
    return grounded_analysis, coverage, rejected
