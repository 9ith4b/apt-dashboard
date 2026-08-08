from apt_hunter import models  # noqa: F401
from apt_hunter.db.base import Base


def test_initial_metadata_contains_intelligence_tables() -> None:
    assert set(Base.metadata.tables) == {
        "sources",
        "reports",
        "threat_events",
        "event_reports",
    }
