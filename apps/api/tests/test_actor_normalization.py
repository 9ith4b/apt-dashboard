from apt_hunter.services.actor_normalization import (
    normalize_actor_key,
    resolve_actor_profile,
    split_actor_names,
)


def test_known_aliases_resolve_to_one_canonical_actor() -> None:
    profile = resolve_actor_profile("Midnight Blizzard / APT29")

    assert profile.canonical_name == "Midnight Blizzard"
    assert "APT29" in profile.aliases
    assert normalize_actor_key("APT-29") == "apt29"


def test_unknown_cluster_remains_independent() -> None:
    profile = resolve_actor_profile("STORM-2945")

    assert profile.canonical_name == "STORM-2945"
    assert profile.aliases == ()
    assert split_actor_names("Alpha / Beta aka Gamma") == ["Alpha", "Beta", "Gamma"]
