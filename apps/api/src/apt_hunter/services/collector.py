import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import Report, Source
from apt_hunter.services.rss import FeedFetchResult, FeedItem, fetch_feed, score_apt_relevance

FeedFetcher = Callable[..., FeedFetchResult]


@dataclass(frozen=True, slots=True)
class CollectionResult:
    source_id: UUID
    fetched: int
    inserted: int
    duplicates: int
    candidates: int
    not_modified: bool

    def as_dict(self) -> dict[str, str | int | bool]:
        return {
            "source_id": str(self.source_id),
            "fetched": self.fetched,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "candidates": self.candidates,
            "not_modified": self.not_modified,
        }


def _exact_hash(item: FeedItem) -> str:
    normalized = " ".join(f"{item.title}\n{item.summary}".split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _record_failure(source_id: UUID, message: str) -> None:
    now = datetime.now(UTC)
    with SessionLocal() as session:
        source = session.get(Source, source_id)
        if source is None:
            return
        source.last_checked_at = now
        source.consecutive_failures += 1
        source.health_status = "degraded"
        source.last_error = message[:1000]
        backoff_minutes = min(
            source.poll_interval_minutes * (2 ** min(source.consecutive_failures, 4)),
            1440,
        )
        source.next_poll_at = now + timedelta(minutes=backoff_minutes)
        session.commit()


def collect_rss_source(
    source_id: UUID,
    *,
    fetcher: FeedFetcher = fetch_feed,
) -> CollectionResult:
    settings = get_settings()
    now = datetime.now(UTC)
    try:
        with SessionLocal() as session:
            source = session.get(Source, source_id)
            if source is None:
                raise ValueError("Source not found")
            if source.type != "rss" or not source.url:
                raise ValueError("Source is not a configured RSS feed")
            source_url = source.url
            etag = source.etag
            last_modified = source.last_modified
            poll_interval_minutes = source.poll_interval_minutes

        result = fetcher(
            source_url,
            etag=etag,
            last_modified=last_modified,
            timeout_seconds=settings.rss_timeout_seconds,
            user_agent=settings.rss_user_agent,
        )

        with SessionLocal() as session:
            source = session.get(Source, source_id)
            if source is None:
                raise ValueError("Source was deleted while polling")
            inserted = 0
            duplicates = 0
            candidates = 0
            for item in result.items:
                exact_hash = _exact_hash(item)
                relevance_score, relevance_reasons = score_apt_relevance(item.title, item.summary)
                status_value = (
                    "candidate"
                    if relevance_score >= settings.rss_relevance_threshold
                    else "filtered"
                )
                existing = session.scalar(
                    select(Report)
                    .where(
                        or_(
                            Report.canonical_url == item.url,
                            Report.exact_hash == exact_hash,
                        )
                    )
                    .limit(1)
                )
                if existing is not None:
                    existing.relevance_score = relevance_score
                    existing.relevance_reasons = relevance_reasons
                    existing.status = status_value
                    duplicates += 1
                    if status_value == "candidate":
                        candidates += 1
                    continue
                if status_value == "candidate":
                    candidates += 1
                session.add(
                    Report(
                        source_id=source.id,
                        title=item.title,
                        canonical_url=item.url,
                        normalized_text=item.summary,
                        exact_hash=exact_hash,
                        relevance_score=relevance_score,
                        relevance_reasons=relevance_reasons,
                        status=status_value,
                        published_at=item.published_at,
                    )
                )
                inserted += 1

            source.last_checked_at = now
            source.last_success_at = now
            source.next_poll_at = now + timedelta(minutes=poll_interval_minutes)
            source.health_status = "healthy"
            source.consecutive_failures = 0
            source.last_error = None
            source.etag = result.etag
            source.last_modified = result.last_modified
            session.commit()
        return CollectionResult(
            source_id=source_id,
            fetched=len(result.items),
            inserted=inserted,
            duplicates=duplicates,
            candidates=candidates,
            not_modified=result.not_modified,
        )
    except Exception as exc:
        _record_failure(source_id, str(exc))
        raise
