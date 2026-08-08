import ipaddress
import re
from urllib.parse import urlsplit

from apt_hunter.services.rss import canonicalize_url

_URL_PATTERN = re.compile(r"https?://[^\s<>\]\[()\"']+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I)
_IPV4_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_IPV6_PATTERN = re.compile(
    r"(?<![\w:])(?:[0-9A-F]{0,4}:){2,7}[0-9A-F]{0,4}(?![\w:])",
    re.IGNORECASE,
)
_DOMAIN_PATTERN = re.compile(
    r"(?<![@\w-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|ru|cn|co|info|biz|top|xyz|site|online|dev|cloud|app)\b",
    re.IGNORECASE,
)
_HASH_PATTERN = re.compile(
    r"(?<![A-F0-9])(?:[A-F0-9]{64}|[A-F0-9]{40}|[A-F0-9]{32})(?![A-F0-9])", re.I
)
_CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
_ATTACK_PATTERN = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)

_IGNORED_HOSTS = {
    "github.com",
    "linkedin.com",
    "microsoft.com",
    "twitter.com",
    "x.com",
    "youtube.com",
}


def _snippet(text: str, start: int, end: int) -> str:
    left_breaks = [text.rfind(mark, 0, start) for mark in ("\n", ". ", "。", "! ", "? ")]
    left = max(left_breaks) + 1
    right_candidates = [
        position
        for mark in ("\n", ". ", "。", "! ", "? ")
        if (position := text.find(mark, end)) >= 0
    ]
    right = min(right_candidates) + 1 if right_candidates else len(text)
    return " ".join(text[left:right].split())[:500]


def _ignored_host(host: str, publisher_host: str | None) -> bool:
    normalized = host.casefold().removeprefix("www.").rstrip(".")
    if publisher_host:
        publisher = publisher_host.casefold().removeprefix("www.").rstrip(".")
        if normalized == publisher or normalized.endswith(f".{publisher}"):
            return True
    return any(normalized == item or normalized.endswith(f".{item}") for item in _IGNORED_HOSTS)


def _candidate(
    observable_type: str,
    original: str,
    normalized: str,
    scope: str,
    confidence: int,
    text: str,
    start: int,
    end: int,
) -> dict[str, object]:
    return {
        "type": observable_type,
        "value": original,
        "normalized": normalized,
        "scope": scope,
        "confidence": confidence,
        "evidence": _snippet(text, start, end),
        "start_offset": start,
        "end_offset": end,
    }


def extract_observables(
    text: str,
    *,
    publisher_url: str | None = None,
) -> list[dict[str, object]]:
    publisher_host = urlsplit(publisher_url).hostname if publisher_url else None
    found: dict[tuple[str, str], dict[str, object]] = {}

    def add(candidate: dict[str, object]) -> None:
        key = (str(candidate["type"]), str(candidate["normalized"]))
        found.setdefault(key, candidate)

    for match in _URL_PATTERN.finditer(text):
        original = match.group(0).rstrip(".,;:")
        try:
            normalized = canonicalize_url(original)
        except ValueError:
            continue
        parsed = urlsplit(normalized)
        if not parsed.hostname or _ignored_host(parsed.hostname, publisher_host):
            continue
        end = match.start() + len(original)
        add(_candidate("url", original, normalized, "public", 98, text, match.start(), end))
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            domain = parsed.hostname.casefold().rstrip(".")
            add(_candidate("domain", domain, domain, "public", 96, text, match.start(), end))
        else:
            address_type = "ipv4" if address.version == 4 else "ipv6"
            scope = "public" if address.is_global else "private"
            add(
                _candidate(
                    address_type,
                    parsed.hostname,
                    address.compressed,
                    scope,
                    98,
                    text,
                    match.start(),
                    end,
                )
            )

    for match in _EMAIL_PATTERN.finditer(text):
        original = match.group(0)
        add(
            _candidate(
                "email",
                original,
                original.casefold(),
                "public",
                98,
                text,
                match.start(),
                match.end(),
            )
        )

    for pattern in (_IPV4_PATTERN, _IPV6_PATTERN):
        for match in pattern.finditer(text):
            original = match.group(0)
            try:
                address = ipaddress.ip_address(original)
            except ValueError:
                continue
            observable_type = "ipv4" if address.version == 4 else "ipv6"
            scope = "public" if address.is_global else "private"
            add(
                _candidate(
                    observable_type,
                    original,
                    address.compressed,
                    scope,
                    99,
                    text,
                    match.start(),
                    match.end(),
                )
            )

    for match in _DOMAIN_PATTERN.finditer(text):
        original = match.group(0).rstrip(".")
        normalized = original.casefold()
        if _ignored_host(normalized, publisher_host):
            continue
        add(
            _candidate(
                "domain",
                original,
                normalized,
                "public",
                94,
                text,
                match.start(),
                match.start() + len(original),
            )
        )

    for match in _HASH_PATTERN.finditer(text):
        original = match.group(0)
        observable_type = {32: "md5", 40: "sha1", 64: "sha256"}[len(original)]
        add(
            _candidate(
                observable_type,
                original,
                original.casefold(),
                "public",
                99,
                text,
                match.start(),
                match.end(),
            )
        )

    for match in _CVE_PATTERN.finditer(text):
        original = match.group(0)
        add(
            _candidate(
                "cve",
                original,
                original.upper(),
                "public",
                99,
                text,
                match.start(),
                match.end(),
            )
        )

    def sort_key(item: dict[str, object]) -> tuple[int, str]:
        offset = item.get("start_offset")
        return (offset if isinstance(offset, int) else 0, str(item["type"]))

    return sorted(found.values(), key=sort_key)


def extract_attack_techniques(text: str) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for match in _ATTACK_PATTERN.finditer(text):
        technique_id = match.group(0).upper()
        found.setdefault(
            technique_id,
            {
                "technique_id": technique_id,
                "name": f"MITRE ATT&CK {technique_id}",
                "tactic": None,
                "confidence": 99,
                "evidence": _snippet(text, match.start(), match.end()),
                "start_offset": match.start(),
                "end_offset": match.end(),
            },
        )
    return list(found.values())
