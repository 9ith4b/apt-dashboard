import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import Report, ReportAnalysis
from apt_hunter.services.article import ArticleDocument, fetch_article
from apt_hunter.services.automation import (
    AutomationOutcome,
    apply_automation_decision,
    automation_enabled,
    get_or_create_policy,
    run_ai_automation,
)
from apt_hunter.services.diamond import extract_diamond
from apt_hunter.services.indicator_automation import apply_ai_observable_decisions
from apt_hunter.services.knowledge import persist_report_knowledge

ArticleFetcher = Callable[..., ArticleDocument]


def detect_language(value: str) -> str:
    sample = value[:5000]
    if not sample:
        return "und"
    chinese = sum("\u4e00" <= char <= "\u9fff" for char in sample)
    letters = sum(char.isalpha() for char in sample)
    if chinese >= 20 and chinese / max(letters, 1) >= 0.15:
        return "zh"
    if sum("a" <= char.casefold() <= "z" for char in sample) >= 40:
        return "en"
    return "und"


def analyze_report(
    report_id: UUID,
    *,
    fetcher: ArticleFetcher = fetch_article,
) -> dict[str, str | int]:
    settings = get_settings()
    with SessionLocal() as session:
        report = session.get(Report, report_id)
        if report is None:
            raise ValueError("Report not found")
        analysis = session.get(ReportAnalysis, report_id)
        if analysis is None:
            analysis = ReportAnalysis(report_id=report_id)
            session.add(analysis)
        analysis.extraction_status = "processing"
        ai_enabled = automation_enabled(session)
        analysis.automation_status = "processing" if ai_enabled else "not_configured"
        analysis.extraction_error = None
        article_url = report.canonical_url
        report_title = report.title
        report_relevance_score = report.relevance_score
        session.commit()

    try:
        article = fetcher(
            article_url,
            timeout_seconds=settings.article_timeout_seconds,
            user_agent=settings.rss_user_agent,
            max_bytes=settings.article_max_bytes,
        )
        diamond = extract_diamond(report_title, article.text, publisher_url=article.final_url)
        if ai_enabled:
            outcome, evidence = run_ai_automation(
                report_id=report_id,
                title=report_title,
                content=article.text,
                deterministic=diamond,
                initial_relevance_score=report_relevance_score,
            )
        else:
            outcome, evidence = AutomationOutcome(), diamond.evidence
        with SessionLocal() as session:
            report = session.get(Report, report_id)
            analysis = session.get(ReportAnalysis, report_id)
            if report is None or analysis is None:
                raise ValueError("Report was deleted while it was being analyzed")
            analysis.content_text = article.text
            analysis.content_hash = hashlib.sha256(article.text.encode("utf-8")).hexdigest()
            analysis.final_url = article.final_url
            analysis.content_type = article.content_type
            analysis.fetched_at = datetime.now(UTC)
            analysis.extraction_status = "ready"
            analysis.extraction_error = None
            analysis.actors = outcome.actors or diamond.actors
            analysis.capabilities = outcome.capabilities or diamond.capabilities
            analysis.infrastructure = outcome.infrastructure or diamond.infrastructure
            analysis.victims = outcome.victims or diamond.victims
            analysis.evidence = evidence
            analysis.observables = outcome.observables or diamond.observables
            analysis.attack_techniques = outcome.attack_techniques or diamond.attack_techniques
            analysis.confidence_auto = outcome.confidence or diamond.confidence
            analysis.method_version = outcome.method_version
            analysis.automation_status = outcome.automation_status
            analysis.ai_relevance_score = outcome.relevance_score
            analysis.ai_classification = outcome.classification
            analysis.ai_summary = outcome.summary
            analysis.ai_claims = outcome.claims
            analysis.ai_verification = outcome.verification
            analysis.evidence_coverage = outcome.evidence_coverage
            analysis.decision_reason = outcome.decision_reason
            analysis.model_config_id = outcome.model_config_id
            report.language = detect_language(article.text)
            if outcome.relevance_score is not None:
                report.relevance_score = outcome.relevance_score
            report.status = outcome.report_status
            persist_report_knowledge(
                session,
                report_id=report_id,
                observed_at=report.published_at or report.created_at,
                observables=analysis.observables,
                techniques=analysis.attack_techniques,
                method_version=analysis.method_version,
            )
            session.flush()
            ioc_counts = apply_ai_observable_decisions(
                session,
                report=report,
                candidates=analysis.observables,
                policy=get_or_create_policy(session),
            )
            apply_automation_decision(
                session,
                report=report,
                analysis=analysis,
                outcome=outcome,
            )
            session.commit()
        return {
            "report_id": str(report_id),
            "status": "ready",
            "confidence": outcome.confidence or diamond.confidence,
            "automation_status": outcome.automation_status,
            "ioc_assessed": ioc_counts["assessed"],
            "ioc_promoted": ioc_counts["promoted"],
        }
    except Exception as exc:
        with SessionLocal() as session:
            analysis = session.get(ReportAnalysis, report_id)
            if analysis is not None:
                analysis.extraction_status = "failed"
                analysis.extraction_error = str(exc)[:2000]
                session.commit()
        raise
