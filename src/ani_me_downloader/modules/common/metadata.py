"""High-level metadata orchestrator.

Tries AniList first (richer data, exact next-episode timestamps) and falls
back to Jikan whenever AniList raises. Both adapters are keyed on MAL ID
and return shape-compatible payloads, so callers do not need to care which
source served the response.
"""
from __future__ import annotations

import logging
from typing import Any

from . import anilist, jikan
from .anilist import AniListUnavailable
from .jikan import JikanUnavailable

logger = logging.getLogger(__name__)


class MetadataUnavailable(Exception):
    """Raised when both AniList and Jikan fail for the same request."""


def search(query: str) -> list[dict[str, Any]]:
    """Search anime by title. Returns AniList-shaped media dicts."""
    try:
        return anilist.search(query)
    except AniListUnavailable as exc:
        logger.info("AniList search failed (%s); falling back to Jikan", exc)

    try:
        return jikan.search(query)
    except JikanUnavailable as exc:
        logger.error("Jikan search also failed: %s", exc)
        raise MetadataUnavailable(str(exc)) from exc


def get_airing(mal_id: int) -> dict[str, Any]:
    """Return airing status for the given MAL ID."""
    try:
        return anilist.get_airing(mal_id)
    except AniListUnavailable as exc:
        logger.info(
            "AniList get_airing(%s) failed (%s); falling back to Jikan", mal_id, exc
        )

    try:
        return jikan.get_airing(mal_id)
    except JikanUnavailable as exc:
        logger.error("Jikan get_airing(%s) also failed: %s", mal_id, exc)
        raise MetadataUnavailable(str(exc)) from exc
