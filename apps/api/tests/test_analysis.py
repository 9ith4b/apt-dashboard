from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.models import Report, ReportAnalysis, Source
from apt_hunter.services.analysis import analyze_report, detect_language
from apt_hunter.services.article import ArticleDocument, normalize_article_text
from apt_hunter.services.diamond import extract_diamond


def test_diamond_extraction_uses_explicit_evidence_only() -> None:
    result = extract_diamond(
        "Lazarus uses fake interviews against developers",
        (
            "The Lazarus Group used a fake interview and phishing campaign to deliver malware "
            "to software developers. Analysts observed command and control at evil-example.com."
        ),
        publisher_url="https://research.example.org/article",
    )

    assert [item["name"] for item in result.actors] == ["Lazarus Group"]
    assert "Social engineering" in {item["name"] for item in result.capabilities}
    assert "Technology companies" in {item["name"] for item in result.victims}
    assert "evil-example.com" in {item["name"] for item in result.infrastructure}
    assert result.confidence >= 90


def test_diamond_extraction_leaves_unknown_dimensions_empty() -> None:
    result = extract_diamond("APT28 activity update", "APT28 activity was observed.")

    assert result.actors
    assert result.capabilities == []
    assert result.infrastructure == []
    assert result.victims == []


def test_diamond_extraction_ignores_reference_links_without_ioc_context() -> None:
    result = extract_diamond(
        "APT29 campaign update",
        (
            "APT29 activity was observed. Further reading: "
            "https://research.example.com/background and connectivitycheck.example.com."
        ),
    )

    assert result.infrastructure == []


def test_text_normalization_and_language_detection() -> None:
    assert normalize_article_text("One   line\n\n\nSecond\tline") == "One line\n\nSecond line"
    assert detect_language("APT actors used phishing against technology companies. " * 4) == "en"
    assert detect_language("该攻击组织持续针对政府和科研机构发起网络钓鱼攻击。" * 5) == "zh"


def test_analyze_report_persists_content_and_diamond(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with testing_session.begin() as session:
        source = Source(type="rss", name="Research", url="https://example.org/feed", enabled=True)
        session.add(source)
        session.flush()
        report = Report(
            source_id=source.id,
            title="Midnight Blizzard targets travelers",
            canonical_url="https://example.org/article",
            normalized_text="A new campaign",
            exact_hash="a" * 64,
            relevance_score=90,
            relevance_reasons=["actor"],
            status="candidate",
            published_at=datetime.now(UTC),
        )
        session.add(report)
        session.flush()
        report_id = report.id

    def fake_fetcher(*_: object, **__: object) -> ArticleDocument:
        return ArticleDocument(
            final_url="https://example.org/article",
            content_type="text/html",
            html="<article>content</article>",
            text=(
                "Midnight Blizzard ran a credential phishing campaign against travelers. "
                "The attackers delivered malware and stole credentials. " * 4
            ),
        )

    monkeypatch.setattr("apt_hunter.services.analysis.SessionLocal", testing_session)
    outcome = analyze_report(report_id, fetcher=fake_fetcher)

    with testing_session() as session:
        analysis = session.scalar(
            select(ReportAnalysis).where(ReportAnalysis.report_id == report_id)
        )
        assert analysis is not None
        assert analysis.extraction_status == "ready"
        assert analysis.review_status == "pending"
        assert analysis.actors[0]["name"] == "Midnight Blizzard / APT29"
        assert analysis.content_hash is not None
        assert outcome["status"] == "ready"
    Base.metadata.drop_all(engine)
