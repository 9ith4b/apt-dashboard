import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import Report, ReportAnalysis
from apt_hunter.services.article import ArticleDocument, fetch_article
from apt_hunter.services.diamond import extract_diamond
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
        analysis.extraction_error = None
        article_url = report.canonical_url
        report_title = report.title
        session.commit()

    try:
        article = fetcher(
            article_url,
            timeout_seconds=settings.article_timeout_seconds,
            user_agent=settings.rss_user_agent,
            max_bytes=settings.article_max_bytes,
        )
        diamond = extract_diamond(report_title, article.text, publisher_url=article.final_url)
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
            analysis.actors = diamond.actors
            analysis.capabilities = diamond.capabilities
            analysis.infrastructure = diamond.infrastructure
            analysis.victims = diamond.victims
            analysis.evidence = diamond.evidence
            analysis.observables = diamond.observables
            analysis.attack_techniques = diamond.attack_techniques
            analysis.confidence_auto = diamond.confidence
            analysis.method_version = "rules-v2"
            report.language = detect_language(article.text)
            persist_report_knowledge(
                session,
                report_id=report_id,
                observed_at=report.published_at or report.created_at,
                observables=diamond.observables,
                techniques=diamond.attack_techniques,
                method_version="rules-v2",
            )
            session.commit()
        return {
            "report_id": str(report_id),
            "status": "ready",
            "confidence": diamond.confidence,
        }
    except Exception as exc:
        with SessionLocal() as session:
            analysis = session.get(ReportAnalysis, report_id)
            if analysis is not None:
                analysis.extraction_status = "failed"
                analysis.extraction_error = str(exc)[:2000]
                session.commit()
        raise
