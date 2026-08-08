from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apt_hunter.db.base import Base
from apt_hunter.models import (
    Evidence,
    Observable,
    Report,
    ReportAnalysis,
    ReportObservable,
    ReportTechnique,
    Source,
)
from apt_hunter.services.analysis import analyze_report, detect_language
from apt_hunter.services.article import ArticleDocument, normalize_article_text
from apt_hunter.services.diamond import extract_diamond
from apt_hunter.services.observable_extraction import (
    extract_attack_techniques,
    extract_observables,
)


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


def test_deterministic_observable_and_attack_extraction_keeps_maliciousness_unset() -> None:
    sha256 = "a" * 64
    text = (
        "The actor used 203.0.113.15 and private address 10.0.0.8. "
        "Contact ops@evil-example.com and download https://evil-example.com/payload. "
        f"SHA-256 {sha256}, CVE-2026-12345, and ATT&CK T1566.001 were observed."
    )

    observables = extract_observables(text)
    techniques = extract_attack_techniques(text)

    values = {(item["type"], item["normalized"]) for item in observables}
    assert ("ipv4", "203.0.113.15") in values
    assert ("ipv4", "10.0.0.8") in values
    assert ("email", "ops@evil-example.com") in values
    assert ("sha256", sha256) in values
    assert ("cve", "CVE-2026-12345") in values
    assert techniques[0]["technique_id"] == "T1566.001"
    assert all("malicious" not in item for item in observables)


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
                "The attackers delivered malware from https://evil-example.com/payload, "
                "using T1566.001 and SHA-256 "
                f"{'b' * 64}. " * 4
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
        assert analysis.observables
        assert analysis.attack_techniques[0]["technique_id"] == "T1566.001"
        assert analysis.content_hash is not None
        assert outcome["status"] == "ready"
        assert session.scalar(select(Observable)) is not None
        assert session.scalar(select(ReportObservable)) is not None
        assert session.scalar(select(ReportTechnique)) is not None
        assert session.scalar(select(Evidence)) is not None
    Base.metadata.drop_all(engine)
