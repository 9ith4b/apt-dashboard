import re
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from apt_hunter.models import (
    EventActor,
    EventReport,
    ReportAnalysis,
    ThreatActor,
    ThreatActorAlias,
)

SEPARATOR_PATTERN = re.compile(
    r"\s*(?:/|\||;|,|\baka\b|\balso known as\b)\s*",
    re.IGNORECASE,
)
NON_WORD_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ActorProfile:
    canonical_name: str
    aliases: tuple[str, ...]
    origin_country: str | None = None
    description: str = ""


KNOWN_PROFILES = (
    ActorProfile(
        canonical_name="Midnight Blizzard",
        aliases=(
            "APT29",
            "Cozy Bear",
            "NOBELIUM",
            "BlueBravo",
            "Cloaked Ursa",
            "UNC2452",
            "Dark Halo",
            "The Dukes",
        ),
        origin_country="Russia",
        description="Russian state-sponsored espionage actor also widely tracked as APT29.",
    ),
    ActorProfile(
        canonical_name="Forest Blizzard",
        aliases=(
            "APT28",
            "Fancy Bear",
            "Sofacy",
            "Sednit",
            "Pawn Storm",
            "STRONTIUM",
        ),
        origin_country="Russia",
        description="Russian state-sponsored actor also widely tracked as APT28.",
    ),
    ActorProfile(
        canonical_name="Lazarus Group",
        aliases=(
            "Lazarus",
            "Hidden Cobra",
            "ZINC",
            "Diamond Sleet",
            "Labyrinth Chollima",
        ),
        origin_country="North Korea",
        description=(
            "North Korean state-sponsored umbrella group tracked across espionage "
            "and financial operations."
        ),
    ),
    ActorProfile(
        canonical_name="Volt Typhoon",
        aliases=("Bronze Silhouette", "Vanguard Panda", "UNC3236", "DEV-0391"),
        origin_country="China",
    ),
    ActorProfile(
        canonical_name="Salt Typhoon",
        aliases=("GhostEmperor", "FamousSparrow", "Earth Estries", "UNC2286"),
        origin_country="China",
    ),
)


def normalize_actor_key(value: str) -> str:
    return NON_WORD_PATTERN.sub("", value.casefold())


def split_actor_names(value: str) -> list[str]:
    return [part.strip() for part in SEPARATOR_PATTERN.split(value) if part.strip()]


PROFILE_BY_ALIAS = {
    normalize_actor_key(alias): profile
    for profile in KNOWN_PROFILES
    for alias in (profile.canonical_name, *profile.aliases)
}


def resolve_actor_profile(reported_name: str) -> ActorProfile:
    names = split_actor_names(reported_name) or [reported_name.strip()]
    for name in names:
        profile = PROFILE_BY_ALIAS.get(normalize_actor_key(name))
        if profile is not None:
            return profile
    canonical_name = names[0]
    return ActorProfile(canonical_name=canonical_name, aliases=tuple(names[1:]))


def _actor_id(canonical_key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"apt-hunter:threat-actor:{canonical_key}")


def _upsert_actor(session: Session, profile: ActorProfile) -> UUID:
    canonical_key = normalize_actor_key(profile.canonical_name)
    actor_id = _actor_id(canonical_key)
    values = {
        "id": actor_id,
        "canonical_name": profile.canonical_name,
        "canonical_key": canonical_key,
        "origin_country": profile.origin_country,
        "description": profile.description,
    }
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(ThreatActor)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[ThreatActor.canonical_key],
                set_={
                    "canonical_name": profile.canonical_name,
                    "origin_country": profile.origin_country,
                    "description": profile.description,
                },
            )
        )
    elif session.get(ThreatActor, actor_id) is None:
        session.add(ThreatActor(**values))
        session.flush()
    return actor_id


def _upsert_alias(session: Session, actor_id: UUID, alias: str) -> None:
    alias_key = normalize_actor_key(alias)
    if not alias_key:
        return
    values = {"alias_key": alias_key, "actor_id": actor_id, "alias": alias}
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(ThreatActorAlias)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[ThreatActorAlias.alias_key],
                set_={"actor_id": actor_id, "alias": alias},
            )
        )
    else:
        existing = session.get(ThreatActorAlias, alias_key)
        if existing is None:
            session.add(ThreatActorAlias(**values))
        else:
            existing.actor_id = actor_id
            existing.alias = alias


def sync_event_actors(
    session: Session,
    event_id: UUID,
    actor_entities: list[dict[str, object]],
) -> None:
    session.execute(delete(EventActor).where(EventActor.event_id == event_id))
    links: dict[UUID, EventActor] = {}
    for entity in actor_entities:
        reported_name = str(entity.get("name", "")).strip()
        if not reported_name:
            continue
        profile = resolve_actor_profile(reported_name)
        actor_id = _upsert_actor(session, profile)
        for alias in {
            profile.canonical_name,
            *profile.aliases,
            *split_actor_names(reported_name),
        }:
            _upsert_alias(session, actor_id, alias)
        confidence_value = entity.get("confidence", 0)
        confidence = int(confidence_value) if isinstance(confidence_value, (int, float)) else 0
        evidence = str(entity.get("evidence", ""))
        current = links.get(actor_id)
        if current is None or confidence > current.confidence:
            links[actor_id] = EventActor(
                event_id=event_id,
                actor_id=actor_id,
                reported_name=reported_name,
                confidence=max(0, min(100, confidence)),
                evidence=evidence,
            )
    session.add_all(links.values())


def sync_event_actors_from_reports(session: Session, event_id: UUID) -> None:
    actor_entities: list[dict[str, object]] = []
    analyses = session.scalars(
        select(ReportAnalysis)
        .join(EventReport, EventReport.report_id == ReportAnalysis.report_id)
        .where(EventReport.event_id == event_id)
    )
    for analysis in analyses:
        actor_entities.extend(
            analysis.reviewed_actors if analysis.reviewed_actors is not None else analysis.actors
        )
    sync_event_actors(session, event_id, actor_entities)
