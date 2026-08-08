import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from apt_hunter.services.observable_extraction import (
    extract_attack_techniques,
    extract_observables,
)

_SENTENCE_BREAK = re.compile(r"(?<=[.!?。！？])\s+|\n+")
_APT_PATTERN = re.compile(
    r"\b(?:APT[- ]?\d{1,3}|UNC\d{3,5}|FIN\d{3,5}|STORM-\d{3,5}|DEV-\d{3,5})\b", re.I
)
_URL_PATTERN = re.compile(r"https?://[^\s<>\]\[()\"']+", re.I)
_DOMAIN_PATTERN = re.compile(
    r"(?<![@\w-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|io|ru|cn|co|info|biz|top|xyz|site|online)\b",
    re.I,
)
_IP_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")

_ACTOR_ALIASES = {
    "midnight blizzard": "Midnight Blizzard / APT29",
    "apt29": "Midnight Blizzard / APT29",
    "cozy bear": "Midnight Blizzard / APT29",
    "nobelium": "Midnight Blizzard / APT29",
    "forest blizzard": "Forest Blizzard / APT28",
    "apt28": "Forest Blizzard / APT28",
    "fancy bear": "Forest Blizzard / APT28",
    "lazarus group": "Lazarus Group",
    "lazarus": "Lazarus Group",
    "kimsuky": "Kimsuky",
    "sandworm": "Sandworm",
    "turla": "Turla",
    "volt typhoon": "Volt Typhoon",
    "salt typhoon": "Salt Typhoon",
    "silk typhoon": "Silk Typhoon",
    "flax typhoon": "Flax Typhoon",
    "star blizzard": "Star Blizzard",
    "secret blizzard": "Secret Blizzard",
    "muddywater": "MuddyWater",
    "oilrig": "OilRig",
}
_CAPABILITIES = {
    "Spear phishing": ("spear phishing", "spearphishing", "targeted phishing"),
    "Phishing": ("phishing", "credential harvesting", "fake login"),
    "Malware delivery": ("malware", "backdoor", "trojan", "implant", "payload"),
    "Credential theft": ("credential theft", "steals credentials", "password spray", "token theft"),
    "Vulnerability exploitation": ("exploit", "zero-day", "0-day", "cve-"),
    "Supply-chain compromise": ("supply chain", "supply-chain"),
    "Ransomware": ("ransomware", "data extortion"),
    "Social engineering": ("fake interview", "job interview", "social engineering", "clickfix"),
    "Command and control": ("command and control", "command-and-control", " c2 "),
}
_VICTIMS = {
    "Government": ("government", "public sector", "ministry", "federal agency"),
    "Diplomats": ("diplomat", "embassy", "foreign affairs"),
    "Technology companies": (
        "technology company",
        "tech companies",
        "software developer",
        "developers",
    ),
    "Hospitality": ("hospitality", "hotel", "travel sector"),
    "Critical infrastructure": ("critical infrastructure", "energy sector", "water utility"),
    "Defense": ("defense sector", "defence sector", "military"),
    "Researchers": ("researcher", "academia", "university"),
    "Travelers": ("traveler", "traveller"),
    "Financial services": ("financial institution", "banking sector", "cryptocurrency company"),
}
_IGNORED_DOMAINS = {
    "microsoft.com",
    "github.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
}

_INFRASTRUCTURE_CONTEXT = (
    "actor-controlled",
    "beacon",
    "command and control",
    "infrastructure",
    "ioc",
    "indicator",
    "malicious",
)


@dataclass(frozen=True, slots=True)
class DiamondResult:
    actors: list[dict[str, object]]
    capabilities: list[dict[str, object]]
    infrastructure: list[dict[str, object]]
    victims: list[dict[str, object]]
    evidence: list[dict[str, object]]
    observables: list[dict[str, object]]
    attack_techniques: list[dict[str, object]]
    confidence: int


def _snippet(text: str, needle: str) -> str:
    for sentence in _SENTENCE_BREAK.split(text):
        if needle.casefold() in sentence.casefold():
            clean = " ".join(sentence.split())
            return clean[:280]
    return ""


def _entity(name: str, entity_type: str, confidence: int, evidence: str) -> dict[str, object]:
    return {
        "name": name,
        "type": entity_type,
        "confidence": confidence,
        "evidence": evidence,
    }


def _has_infrastructure_context(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in _INFRASTRUCTURE_CONTEXT)


def _is_global_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def _host_is_ignored(host: str, publisher_host: str | None) -> bool:
    normalized = host.casefold().removeprefix("www.")
    if publisher_host:
        publisher = publisher_host.casefold().removeprefix("www.")
        if normalized == publisher or normalized.endswith(f".{publisher}"):
            return True
    return any(normalized == item or normalized.endswith(f".{item}") for item in _IGNORED_DOMAINS)


def extract_diamond(
    title: str,
    content: str,
    *,
    publisher_url: str | None = None,
) -> DiamondResult:
    text = f"{title}\n{content}"
    lowered = text.casefold()
    actors_by_name: dict[str, dict[str, object]] = {}
    for alias, canonical in _ACTOR_ALIASES.items():
        if alias in lowered:
            actors_by_name.setdefault(
                canonical, _entity(canonical, "threat-actor", 90, _snippet(text, alias))
            )
    for match in _APT_PATTERN.finditer(text):
        raw_name = match.group(0).upper().replace(" ", "")
        canonical = _ACTOR_ALIASES.get(raw_name.casefold(), raw_name)
        actors_by_name.setdefault(
            canonical, _entity(canonical, "threat-actor", 85, _snippet(text, match.group(0)))
        )

    capabilities: list[dict[str, object]] = []
    for name, keywords in _CAPABILITIES.items():
        matched = next((keyword for keyword in keywords if keyword in lowered), None)
        if matched:
            capabilities.append(_entity(name, "capability", 78, _snippet(text, matched)))

    publisher_host = urlsplit(publisher_url).hostname if publisher_url else None
    infrastructure: list[dict[str, object]] = []
    seen_infrastructure: set[str] = set()
    for match in _URL_PATTERN.finditer(text):
        value = match.group(0).rstrip(".,;:")
        host = urlsplit(value).hostname
        evidence_snippet = _snippet(text, value)
        if (
            not host
            or _host_is_ignored(host, publisher_host)
            or value.casefold() in seen_infrastructure
        ):
            continue
        if not _is_global_ip(host) and not _has_infrastructure_context(evidence_snippet):
            continue
        seen_infrastructure.add(value.casefold())
        infrastructure.append(_entity(value, "url", 88, evidence_snippet))
    for match in _IP_PATTERN.finditer(text):
        value = match.group(0)
        if not _is_global_ip(value):
            continue
        if value in seen_infrastructure:
            continue
        seen_infrastructure.add(value)
        infrastructure.append(_entity(value, "ipv4", 92, _snippet(text, value)))
    for match in _DOMAIN_PATTERN.finditer(text):
        value = match.group(0).casefold()
        evidence_snippet = _snippet(text, value)
        if (
            _host_is_ignored(value, publisher_host)
            or value in seen_infrastructure
            or not _has_infrastructure_context(evidence_snippet)
        ):
            continue
        seen_infrastructure.add(value)
        infrastructure.append(_entity(value, "domain", 82, evidence_snippet))
    infrastructure = infrastructure[:20]

    victims: list[dict[str, object]] = []
    for name, keywords in _VICTIMS.items():
        matched = next((keyword for keyword in keywords if keyword in lowered), None)
        if matched:
            victims.append(_entity(name, "victim-sector", 76, _snippet(text, matched)))

    dimensions = {
        "adversary": list(actors_by_name.values()),
        "capability": capabilities,
        "infrastructure": infrastructure,
        "victim": victims,
    }
    evidence = [
        {"dimension": dimension, "entity": item["name"], "quote": item["evidence"]}
        for dimension, items in dimensions.items()
        for item in items
        if item["evidence"]
    ][:40]
    populated = sum(bool(items) for items in dimensions.values())
    confidence = min(95, 35 + populated * 14 + (5 if actors_by_name else 0))
    return DiamondResult(
        actors=list(actors_by_name.values()),
        capabilities=capabilities,
        infrastructure=infrastructure,
        victims=victims,
        evidence=evidence,
        observables=extract_observables(content, publisher_url=publisher_url),
        attack_techniques=extract_attack_techniques(content),
        confidence=confidence,
    )
