import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import feedparser
import httpx

_WHITESPACE = re.compile(r"\s+")
_APT_PATTERN = re.compile(r"\bAPT[- ]?\d{1,3}\b", re.IGNORECASE)
_VENDOR_ACTOR_PATTERN = re.compile(r"\b(?:DEV|STORM)[- ]?\d{3,5}\b", re.IGNORECASE)
_UNC_PATTERN = re.compile(r"\b(?:UNC|FIN)\d{3,5}\b", re.IGNORECASE)
_TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}
_NAMED_ACTORS = {
    "cozy bear",
    "fancy bear",
    "flax typhoon",
    "forest blizzard",
    "kimsuky",
    "lazarus",
    "lazarus group",
    "midnight blizzard",
    "muddywater",
    "oilrig",
    "salt typhoon",
    "sandworm",
    "secret blizzard",
    "silk typhoon",
    "star blizzard",
    "turla",
    "velvet ant",
    "volt typhoon",
}
_ATTACK_TERMS = {
    "backdoor",
    "campaign",
    "credential",
    "cyberespionage",
    "exploit",
    "intrusion",
    "malware",
    "phishing",
    "ransomware",
    "supply chain",
    "攻击",
    "恶意软件",
    "漏洞利用",
    "网络钓鱼",
}
_SUPPORTED_FEED_TYPES = {
    "application/atom+xml",
    "application/rss+xml",
    "application/xml",
    "text/xml",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


@dataclass(frozen=True, slots=True)
class FeedItem:
    title: str
    url: str
    summary: str
    author: str | None
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class FeedFetchResult:
    items: list[FeedItem]
    etag: str | None
    last_modified: str | None
    not_modified: bool = False


def strip_markup(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return _WHITESPACE.sub(" ", " ".join(parser.parts)).strip()


def canonicalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("RSS entries must contain an HTTP(S) URL")
    filtered_query = []
    for key, item_value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in _TRACKING_PARAMETERS:
            continue
        filtered_query.append((key, item_value))
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def _published_at(entry: object) -> datetime | None:
    if not isinstance(entry, dict):
        return None
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not isinstance(parsed, time.struct_time):
        return None
    return datetime(*parsed[:6], tzinfo=UTC)


def parse_rss_document(payload: bytes) -> list[FeedItem]:
    document = feedparser.parse(payload)
    entries = document.get("entries", [])
    if document.get("bozo") and not entries:
        raise ValueError("The RSS document could not be parsed")

    items: list[FeedItem] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        title = strip_markup(str(raw_entry.get("title", "")))
        raw_url = str(raw_entry.get("link", "")).strip()
        if not title or not raw_url:
            continue
        try:
            url = canonicalize_url(raw_url)
        except ValueError:
            continue
        summary = strip_markup(str(raw_entry.get("summary") or raw_entry.get("description") or ""))
        raw_author = str(raw_entry.get("author", "")).strip()
        items.append(
            FeedItem(
                title=title,
                url=url,
                summary=summary,
                author=raw_author or None,
                published_at=_published_at(raw_entry),
            )
        )
    return items


def validate_public_feed_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("RSS feed URL must use HTTP(S)")
    if parsed.username or parsed.password:
        raise ValueError("RSS feed URL must not contain credentials")

    try:
        addresses = {
            result[4][0]
            for result in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise ValueError("RSS feed hostname could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("RSS feed URL must resolve only to public IP addresses")


def validate_connected_peer(response: httpx.Response) -> None:
    stream = response.extensions.get("network_stream")
    if stream is None or not hasattr(stream, "get_extra_info"):
        return
    peer = stream.get_extra_info("server_addr") or stream.get_extra_info("peername")
    address = peer[0] if isinstance(peer, tuple) and peer else peer
    if isinstance(address, str) and not ipaddress.ip_address(address).is_global:
        raise ValueError("Connected peer is not a public IP address")


def fetch_feed(
    url: str,
    *,
    etag: str | None,
    last_modified: str | None,
    timeout_seconds: float,
    user_agent: str,
    max_bytes: int = 2_097_152,
    max_compression_ratio: int = 100,
) -> FeedFetchResult:
    headers = {"Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml"}
    headers["User-Agent"] = user_agent
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    current_url = url
    with httpx.Client(timeout=timeout_seconds, follow_redirects=False, headers=headers) as client:
        for _ in range(6):
            validate_public_feed_url(current_url)
            response = client.get(current_url)
            if not response.has_redirect_location:
                break
            location = response.headers.get("location")
            if not location:
                raise ValueError("RSS feed redirect did not include a destination")
            current_url = urljoin(current_url, location)
        else:
            raise ValueError("RSS feed exceeded the redirect limit")
    if response.status_code == httpx.codes.NOT_MODIFIED:
        return FeedFetchResult(
            items=[],
            etag=response.headers.get("etag") or etag,
            last_modified=response.headers.get("last-modified") or last_modified,
            not_modified=True,
        )
    response.raise_for_status()
    validate_connected_peer(response)
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type and content_type not in _SUPPORTED_FEED_TYPES:
        raise ValueError(f"Unsupported feed content type: {content_type}")
    payload = response.content
    if len(payload) > max_bytes:
        raise ValueError("RSS feed exceeds the configured size limit")
    declared_length = response.headers.get("content-length")
    if response.headers.get("content-encoding") and declared_length:
        try:
            compressed_bytes = max(int(declared_length), 1)
        except ValueError as exc:
            raise ValueError("RSS feed returned an invalid content length") from exc
        if len(payload) / compressed_bytes > max_compression_ratio:
            raise ValueError("RSS feed exceeded the compression ratio limit")
    return FeedFetchResult(
        items=parse_rss_document(payload),
        etag=response.headers.get("etag"),
        last_modified=response.headers.get("last-modified"),
    )


def score_apt_relevance(title: str, summary: str) -> tuple[int, list[str]]:
    text = f"{title} {summary}"
    lowered = text.casefold()
    reasons: list[str] = []
    score = 0

    actor_match = (
        _APT_PATTERN.search(text) or _UNC_PATTERN.search(text) or _VENDOR_ACTOR_PATTERN.search(text)
    )
    named_actor = next((actor for actor in _NAMED_ACTORS if actor in lowered), None)
    if actor_match:
        score += 65
        reasons.append(f"命中攻击组织：{actor_match.group(0).upper()}")
    elif named_actor:
        score += 65
        reasons.append(f"命中攻击组织：{named_actor}")

    matched_terms = sorted(term for term in _ATTACK_TERMS if term in lowered)
    if matched_terms:
        score += min(30, 10 + len(matched_terms) * 5)
        reasons.append(f"命中攻击语义：{', '.join(matched_terms[:3])}")

    if "cve-" in lowered or "zero-day" in lowered or "0-day" in lowered:
        score += 10
        reasons.append("包含漏洞或零日利用信号")

    return min(score, 100), reasons
