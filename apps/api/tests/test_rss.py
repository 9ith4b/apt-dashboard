import gzip
from typing import Any

import httpx
import pytest

from apt_hunter.services.rss import (
    canonicalize_url,
    fetch_feed,
    parse_rss_document,
    score_apt_relevance,
    validate_public_feed_url,
)

RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Security Research</title>
    <item>
      <title>APT28 launches credential phishing campaign</title>
      <link>https://example.com/research/apt28?utm_source=newsletter&amp;id=42</link>
      <description><![CDATA[The campaign deploys new malware against diplomats.]]></description>
      <pubDate>Fri, 08 Aug 2026 04:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_document_normalizes_entries() -> None:
    items = parse_rss_document(RSS_SAMPLE)

    assert len(items) == 1
    assert items[0].title == "APT28 launches credential phishing campaign"
    assert items[0].url == "https://example.com/research/apt28?id=42"
    assert items[0].summary == "The campaign deploys new malware against diplomats."
    assert items[0].published_at is not None


def test_apt_relevance_requires_actor_and_attack_context() -> None:
    score, reasons = score_apt_relevance(
        "Lazarus uses fake interviews",
        "The phishing campaign delivers malware to developers.",
    )

    assert score >= 80
    assert any("攻击组织" in reason for reason in reasons)
    assert any("攻击语义" in reason for reason in reasons)


def test_generic_security_article_stays_below_candidate_threshold() -> None:
    score, reasons = score_apt_relevance(
        "Quarterly security update",
        "The vendor published routine product guidance.",
    )

    assert score < 50
    assert reasons == []


def test_microsoft_actor_alias_is_a_candidate() -> None:
    score, reasons = score_apt_relevance(
        "Midnight Blizzard targets travelers worldwide",
        "The operation delivers malware and steals credentials.",
    )

    assert score >= 80
    assert any("midnight blizzard" in reason for reason in reasons)


def test_canonicalize_url_rejects_non_http_urls() -> None:
    try:
        canonicalize_url("javascript:alert(1)")
    except ValueError as exc:
        assert "HTTP(S)" in str(exc)
    else:
        raise AssertionError("Expected a ValueError")


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/feed", "http://169.254.169.254/latest/meta-data", "http://[::1]/"],
)
def test_validate_public_feed_url_rejects_non_public_addresses(url: str) -> None:
    with pytest.raises(ValueError, match="public IP"):
        validate_public_feed_url(url)


def test_fetch_feed_treats_304_as_not_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        httpx.codes.NOT_MODIFIED,
        headers={"etag": '"next-etag"'},
        request=httpx.Request("GET", "https://example.com/feed"),
    )

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_: Any) -> None:
            pass

        def get(self, _: str) -> httpx.Response:
            return response

    monkeypatch.setattr("apt_hunter.services.rss.validate_public_feed_url", lambda _: None)
    monkeypatch.setattr("apt_hunter.services.rss.httpx.Client", FakeClient)

    result = fetch_feed(
        "https://example.com/feed",
        etag='"previous-etag"',
        last_modified=None,
        timeout_seconds=5,
        user_agent="APT-Hunter-Test",
    )

    assert result.not_modified is True
    assert result.etag == '"next-etag"'
    assert result.items == []


def test_fetch_feed_rejects_mime_size_and_compression_bombs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        httpx.Response(
            200,
            content=b"not a feed",
            headers={"content-type": "application/octet-stream"},
            request=httpx.Request("GET", "https://example.com/feed"),
        ),
        httpx.Response(
            200,
            content=gzip.compress(RSS_SAMPLE),
            headers={
                "content-type": "application/rss+xml",
                "content-encoding": "gzip",
                "content-length": "1",
            },
            request=httpx.Request("GET", "https://example.com/feed"),
        ),
    ]

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_: Any) -> None:
            pass

        def get(self, _: str) -> httpx.Response:
            return responses.pop(0)

    monkeypatch.setattr("apt_hunter.services.rss.validate_public_feed_url", lambda _: None)
    monkeypatch.setattr("apt_hunter.services.rss.httpx.Client", FakeClient)
    arguments = {
        "etag": None,
        "last_modified": None,
        "timeout_seconds": 5,
        "user_agent": "APT-Hunter-Test",
    }

    with pytest.raises(ValueError, match="content type"):
        fetch_feed("https://example.com/feed", **arguments)
    with pytest.raises(ValueError, match="compression ratio"):
        fetch_feed("https://example.com/feed", max_compression_ratio=10, **arguments)
