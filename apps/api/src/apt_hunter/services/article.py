import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import trafilatura

from apt_hunter.services.rss import validate_connected_peer, validate_public_feed_url

_WHITESPACE = re.compile(r"[ \t\f\v]+")
_PARAGRAPH_BREAKS = re.compile(r"\n{3,}")
_SUPPORTED_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}


@dataclass(frozen=True, slots=True)
class ArticleDocument:
    final_url: str
    content_type: str
    html: str
    text: str


def normalize_article_text(value: str) -> str:
    lines = [_WHITESPACE.sub(" ", line).strip() for line in value.splitlines()]
    return _PARAGRAPH_BREAKS.sub("\n\n", "\n".join(lines)).strip()


def fetch_article(
    url: str,
    *,
    timeout_seconds: float,
    user_agent: str,
    max_bytes: int,
    max_compression_ratio: int = 100,
) -> ArticleDocument:
    headers = {
        "Accept": "text/html, application/xhtml+xml, text/plain;q=0.8",
        "User-Agent": user_agent,
    }
    current_url = url
    payload = b""
    content_type = ""
    encoding = "utf-8"

    with httpx.Client(timeout=timeout_seconds, follow_redirects=False, headers=headers) as client:
        for _ in range(6):
            validate_public_feed_url(current_url)
            with client.stream("GET", current_url) as response:
                if response.has_redirect_location:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Article redirect did not include a destination")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                validate_connected_peer(response)
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in _SUPPORTED_CONTENT_TYPES:
                    raise ValueError(
                        f"Unsupported article content type: {content_type or 'unknown'}"
                    )
                declared_length = response.headers.get("content-length")
                if declared_length and int(declared_length) > max_bytes:
                    raise ValueError("Article exceeds the configured size limit")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Article exceeds the configured size limit")
                    chunks.append(chunk)
                if response.headers.get("content-encoding") and declared_length:
                    try:
                        compressed_bytes = max(int(declared_length), 1)
                    except ValueError as exc:
                        raise ValueError("Article returned an invalid content length") from exc
                    if total / compressed_bytes > max_compression_ratio:
                        raise ValueError("Article exceeded the compression ratio limit")
                payload = b"".join(chunks)
                encoding = response.charset_encoding or "utf-8"
                break
        else:
            raise ValueError("Article exceeded the redirect limit")

    extracted: str | None
    html = payload.decode(encoding, errors="replace")
    if content_type == "text/plain":
        extracted = html
    else:
        extracted = trafilatura.extract(
            html,
            output_format="txt",
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            url=current_url,
        )
        if not extracted:
            extracted = trafilatura.html2txt(html)
    text = normalize_article_text(extracted or "")
    if len(text) < 120:
        raise ValueError("Article main text was empty or too short")
    return ArticleDocument(
        final_url=current_url,
        content_type=content_type,
        html=html,
        text=text,
    )
