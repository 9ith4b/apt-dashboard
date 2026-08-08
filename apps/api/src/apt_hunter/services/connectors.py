import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import httpx

from apt_hunter.config import Settings
from apt_hunter.models import Source
from apt_hunter.services.article import fetch_article
from apt_hunter.services.rss import FeedItem, fetch_feed

ConnectorType = Literal["rss", "web", "x", "telegram"]
_MAX_API_RESPONSE_BYTES = 2_097_152
_ALLOWED_SECRET_REFS = {
    "APT_HUNTER_X_BEARER_TOKEN",
    "APT_HUNTER_TELEGRAM_BOT_TOKEN",
}


@dataclass(frozen=True, slots=True)
class ConnectorPage:
    items: list[FeedItem]
    cursor: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    next_poll_at: datetime | None = None


def _secret(source: Source) -> str:
    if source.secret_ref not in _ALLOWED_SECRET_REFS:
        raise ValueError("Connector secret reference is not allowlisted")
    value = os.getenv(source.secret_ref)
    if not value:
        raise ValueError(f"Connector credential {source.secret_ref} is not configured")
    return value


def _json_payload(response: httpx.Response, provider: str) -> dict[str, object]:
    if response.status_code >= 400:
        raise ValueError(f"{provider} API returned HTTP {response.status_code}")
    if len(response.content) > _MAX_API_RESPONSE_BYTES:
        raise ValueError(f"{provider} API response exceeded the size limit")
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"{provider} API returned an unexpected response")
    return payload


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _rss_page(source: Source, settings: Settings) -> ConnectorPage:
    if not source.url:
        raise ValueError("RSS source URL is missing")
    result = fetch_feed(
        source.url,
        etag=source.etag,
        last_modified=source.last_modified,
        timeout_seconds=settings.rss_timeout_seconds,
        user_agent=settings.rss_user_agent,
    )
    return ConnectorPage(
        items=result.items,
        etag=result.etag,
        last_modified=result.last_modified,
        not_modified=result.not_modified,
    )


def _web_page(source: Source, settings: Settings) -> ConnectorPage:
    if not source.url:
        raise ValueError("Web source URL is missing")
    document = fetch_article(
        source.url,
        timeout_seconds=settings.article_timeout_seconds,
        user_agent=settings.rss_user_agent,
        max_bytes=settings.article_max_bytes,
    )
    title = next((line.strip() for line in document.text.splitlines() if line.strip()), source.name)
    return ConnectorPage(
        items=[
            FeedItem(
                title=title[:500],
                url=document.final_url,
                summary=document.text,
                author=source.name,
                published_at=datetime.now(UTC),
            )
        ]
    )


def _x_page(source: Source, settings: Settings) -> ConnectorPage:
    token = _secret(source)
    query = str(source.config.get("query", "")).strip()
    if not query:
        raise ValueError("X connector query is missing")
    max_results_value = source.config.get("max_results", 25)
    max_results = max(
        10, min(100, int(max_results_value) if isinstance(max_results_value, int) else 25)
    )
    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "created_at,author_id,entities",
    }
    cursor = source.config.get("cursor")
    if isinstance(cursor, str) and cursor:
        params["since_id"] = cursor
    with httpx.Client(
        timeout=settings.rss_timeout_seconds,
        headers={"Authorization": f"Bearer {token}", "User-Agent": settings.rss_user_agent},
    ) as client:
        response = client.get("https://api.x.com/2/tweets/search/recent", params=params)
    payload = _json_payload(response, "X")
    raw_items = payload.get("data", [])
    items: list[FeedItem] = []
    if isinstance(raw_items, list):
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            tweet_id = str(raw.get("id", "")).strip()
            text = str(raw.get("text", "")).strip()
            if not tweet_id or not text:
                continue
            items.append(
                FeedItem(
                    title=text[:160],
                    url=f"https://x.com/i/web/status/{tweet_id}",
                    summary=text,
                    author=str(raw.get("author_id", "")) or None,
                    published_at=_parse_datetime(raw.get("created_at")),
                )
            )
    meta = payload.get("meta")
    newest_id = str(meta.get("newest_id", "")) if isinstance(meta, dict) else ""
    reset = response.headers.get("x-rate-limit-reset")
    next_poll_at = datetime.fromtimestamp(int(reset), tz=UTC) if reset and reset.isdigit() else None
    return ConnectorPage(items=items, cursor=newest_id or None, next_poll_at=next_poll_at)


def _telegram_page(source: Source, settings: Settings) -> ConnectorPage:
    token = _secret(source)
    raw_chat_ids = source.config.get("chat_ids", [])
    allowed_chat_ids = (
        {str(value) for value in raw_chat_ids} if isinstance(raw_chat_ids, list) else set()
    )
    params: dict[str, str] = {"timeout": "0", "limit": "100"}
    cursor = source.config.get("cursor")
    if isinstance(cursor, str) and cursor:
        params["offset"] = cursor
    with httpx.Client(
        timeout=settings.rss_timeout_seconds,
        headers={"User-Agent": settings.rss_user_agent},
    ) as client:
        response = client.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params)
    payload = _json_payload(response, "Telegram")
    if payload.get("ok") is not True:
        raise ValueError("Telegram API returned an unsuccessful response")
    raw_updates = payload.get("result", [])
    items: list[FeedItem] = []
    last_update_id: int | None = None
    if isinstance(raw_updates, list):
        for update in raw_updates:
            if not isinstance(update, dict):
                continue
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                last_update_id = max(last_update_id or update_id, update_id)
            message = update.get("channel_post") or update.get("message")
            if not isinstance(message, dict):
                continue
            chat = message.get("chat")
            if not isinstance(chat, dict):
                continue
            chat_id = str(chat.get("id", ""))
            if allowed_chat_ids and chat_id not in allowed_chat_ids:
                continue
            text = str(message.get("text") or message.get("caption") or "").strip()
            message_id = message.get("message_id")
            if not text or not isinstance(message_id, int):
                continue
            username = str(chat.get("username", "")).strip()
            path_id = chat_id.removeprefix("-100")
            url = (
                f"https://t.me/{username}/{message_id}"
                if username
                else f"https://t.me/c/{path_id}/{message_id}"
            )
            timestamp = message.get("date")
            published_at = (
                datetime.fromtimestamp(timestamp, tz=UTC) if isinstance(timestamp, int) else None
            )
            chat_title = str(chat.get("title") or username or chat_id)
            items.append(
                FeedItem(
                    title=f"{chat_title}: {text[:140]}",
                    url=url,
                    summary=text,
                    author=chat_title,
                    published_at=published_at,
                )
            )
    next_cursor = str(last_update_id + 1) if last_update_id is not None else None
    return ConnectorPage(items=items, cursor=next_cursor)


def fetch_connector_page(source: Source, settings: Settings) -> ConnectorPage:
    if source.type == "rss":
        return _rss_page(source, settings)
    if source.type == "web":
        return _web_page(source, settings)
    if source.type == "x":
        return _x_page(source, settings)
    if source.type == "telegram":
        return _telegram_page(source, settings)
    raise ValueError(f"Unsupported connector type: {source.type}")
