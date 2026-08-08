from typing import Any

import httpx
import pytest

from apt_hunter.config import Settings
from apt_hunter.models import Source
from apt_hunter.services.connectors import fetch_connector_page


class FakeClient:
    response: httpx.Response
    last_url: str = ""
    last_params: dict[str, str] = {}

    def __init__(self, **_: Any) -> None:
        pass

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def get(self, url: str, params: dict[str, str]) -> httpx.Response:
        FakeClient.last_url = url
        FakeClient.last_params = params
        return FakeClient.response


def test_x_connector_uses_official_api_cursor_and_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APT_HUNTER_X_BEARER_TOKEN", "test-bearer")
    monkeypatch.setattr("apt_hunter.services.connectors.httpx.Client", FakeClient)
    FakeClient.response = httpx.Response(
        200,
        json={
            "data": [
                {
                    "id": "1900000000000000000",
                    "text": "APT29 used phishing and malware against diplomats",
                    "author_id": "42",
                    "created_at": "2026-08-08T08:00:00Z",
                }
            ],
            "meta": {"newest_id": "1900000000000000000"},
        },
        headers={"x-rate-limit-reset": "1786179600"},
    )
    source = Source(
        type="x",
        name="APT X search",
        config={"query": "APT OR malware", "cursor": "1899999999999999999"},
        secret_ref="APT_HUNTER_X_BEARER_TOKEN",
    )

    page = fetch_connector_page(source, Settings())

    assert FakeClient.last_url == "https://api.x.com/2/tweets/search/recent"
    assert FakeClient.last_params["since_id"] == "1899999999999999999"
    assert page.cursor == "1900000000000000000"
    assert page.items[0].url == "https://x.com/i/web/status/1900000000000000000"
    assert page.next_poll_at is not None


def test_telegram_connector_filters_chat_and_advances_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APT_HUNTER_TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.setattr("apt_hunter.services.connectors.httpx.Client", FakeClient)
    FakeClient.response = httpx.Response(
        200,
        json={
            "ok": True,
            "result": [
                {
                    "update_id": 101,
                    "channel_post": {
                        "message_id": 7,
                        "date": 1786176000,
                        "chat": {
                            "id": -10012345,
                            "username": "security_feed",
                            "title": "Security Feed",
                        },
                        "text": "Lazarus fake interview campaign delivers malware",
                    },
                },
                {
                    "update_id": 102,
                    "message": {
                        "message_id": 8,
                        "chat": {"id": -10099999, "title": "Ignored"},
                        "text": "Ignored chat",
                    },
                },
            ],
        },
    )
    source = Source(
        type="telegram",
        name="Telegram channel updates",
        config={"chat_ids": ["-10012345"], "cursor": "100"},
        secret_ref="APT_HUNTER_TELEGRAM_BOT_TOKEN",
    )

    page = fetch_connector_page(source, Settings())

    assert FakeClient.last_url.startswith("https://api.telegram.org/bot")
    assert FakeClient.last_params["offset"] == "100"
    assert len(page.items) == 1
    assert page.items[0].url == "https://t.me/security_feed/7"
    assert page.cursor == "103"
