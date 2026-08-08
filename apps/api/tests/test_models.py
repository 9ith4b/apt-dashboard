from apt_hunter import models  # noqa: F401
from apt_hunter.db.base import Base


def test_initial_metadata_contains_intelligence_tables() -> None:
    assert set(Base.metadata.tables) == {
        "analysis_revisions",
        "attack_techniques",
        "event_merge_candidates",
        "event_actors",
        "event_observables",
        "sources",
        "evidence",
        "observables",
        "reports",
        "report_analyses",
        "report_observables",
        "report_techniques",
        "event_techniques",
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


def test_knowledge_foreign_keys_have_reverse_lookup_indexes() -> None:
    tables = Base.metadata.tables

    assert "ix_report_observables_observable_report" in {
        index.name for index in tables["report_observables"].indexes
    }
    assert "ix_event_observables_observable_event" in {
        index.name for index in tables["event_observables"].indexes
    }
    assert "ix_event_merge_candidates_target_event" in {
        index.name for index in tables["event_merge_candidates"].indexes
    }
