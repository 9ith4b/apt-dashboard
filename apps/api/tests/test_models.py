from apt_hunter import models  # noqa: F401
from apt_hunter.db.base import Base


def test_initial_metadata_contains_intelligence_tables() -> None:
    assert set(Base.metadata.tables) == {
        "analysis_revisions",
        "event_actors",
        "sources",
        "reports",
        "report_analyses",
        "threat_actor_aliases",
        "threat_actors",
        "threat_events",
        "event_reports",
    }


def test_rss_polling_indexes_are_registered() -> None:
    source_indexes = {index.name for index in Base.metadata.tables["sources"].indexes}
    report_indexes = {index.name for index in Base.metadata.tables["reports"].indexes}
    analysis_indexes = {index.name for index in Base.metadata.tables["report_analyses"].indexes}

    assert "ix_sources_due_poll" in source_indexes
    assert "ix_reports_source_published_at" in report_indexes
    assert "ix_report_analyses_review_updated" in analysis_indexes
    assert "ix_report_analyses_pending_review" in analysis_indexes
