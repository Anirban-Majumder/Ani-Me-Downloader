# coding: utf-8
"""Episode helpers: display names + initial seeding for non-default modes."""
from .anime import Anime, EpState, EpStatus


def episode_display_name(anime: Anime, ep: int) -> str:
    """Filename-style label. ep == 0 → batch (anime.name)."""
    if ep == 0:
        return anime.name
    return f"{anime.name} S{anime.season:02d}E{ep:02d}"


def seed_episodes(
    *,
    mode: str,
    total_episodes: int,
    from_ep: int = 1,
    to_ep: int | None = None,
) -> list[EpState]:
    """Initial `episodes` list. Lazy model: episodic shows seed nothing
    (pending derived from `Anime.pending_eps`). Only `track_only` mode
    needs explicit records — those eps must be excluded from derivation."""
    if mode == "track_only":
        last = to_ep if to_ep is not None else total_episodes
        return [EpState(ep=i, status=EpStatus.TRACK_ONLY) for i in range(from_ep, last + 1)]
    return []
