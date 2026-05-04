# coding: utf-8
"""Pure torrent selection from a list of NyaaResults."""
import re

from .nyaa import NyaaResult
from .uploader_rules import DEFAULT_RULES, UploaderRule


def _name_regex(name: str, search_name: str) -> re.Pattern:
    n = re.escape(name)
    sn = re.escape(search_name) if search_name else n
    pattern = rf"\b(1080p.*({n}|{sn})|({n}|{sn}).*1080p)\b"
    return re.compile(pattern, re.IGNORECASE)


def _matches_episode_rule(rule: UploaderRule, title_lower: str, season: int, episode: int) -> bool:
    if rule.tag not in title_lower:
        return False
    return rule.episode_pattern.format(season=season, episode=episode) in title_lower


def _fallback_episode_match(title_lower: str, season: int, episode: int) -> bool:
    """Generic season+episode patterns when no uploader rule matches."""
    primary = f" s{season:02d}e{episode:02d} "
    if primary in title_lower:
        return True
    if season < 2 and f" e{episode:02d} " in title_lower:
        return True
    return False


def select_torrent(
    results: list[NyaaResult],
    *,
    name: str,
    search_name: str,
    season: int,
    episode: int | None,
    rules: tuple[UploaderRule, ...] = DEFAULT_RULES,
) -> str | None:
    """Return the magnet of the best matching torrent, or None.

    `episode is None` selects a batch torrent. Results assumed seed-sorted.
    """
    regex = _name_regex(name, search_name)
    season_marker = f"(season {season})" if season > 1 else ""

    for r in results:
        title_lower = r.title.lower()
        if not regex.search(r.title) or "vostfr" in title_lower:
            continue

        if episode is None:
            for rule in rules:
                if not rule.accepts_batch or rule.tag not in title_lower:
                    continue
                if not any(k in title_lower for k in rule.batch_keywords):
                    continue
                if season_marker and season_marker not in title_lower:
                    continue
                return r.magnet
            continue

        for rule in rules:
            if not rule.accepts_episodes:
                continue
            if _matches_episode_rule(rule, title_lower, season, episode):
                return r.magnet
        if _fallback_episode_match(title_lower, season, episode):
            return r.magnet

    return None
