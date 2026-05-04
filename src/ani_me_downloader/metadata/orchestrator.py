# coding: utf-8
"""Metadata orchestrator. AniList → Jikan fallback. Normalizes status to AiringStatus."""
import logging
from typing import Any

from ..core.anime import AiringStatus
from . import anilist, jikan
from .anilist import AniListUnavailable
from .jikan import JikanUnavailable

logger = logging.getLogger(__name__)


class MetadataUnavailable(Exception):
    """Both AniList and Jikan failed for the same request."""


_STATUS_MAP = {
    "RELEASING": AiringStatus.RELEASING,
    "FINISHED": AiringStatus.FINISHED,
    "NOT_YET_RELEASED": AiringStatus.NOT_YET_RELEASED,
    "HIATUS": AiringStatus.HIATUS,
    "CANCELLED": AiringStatus.CANCELLED,
}


def _normalize(info: dict[str, Any]) -> dict[str, Any]:
    raw = info.get("status")
    info["status"] = _STATUS_MAP.get(raw, AiringStatus.UNKNOWN)
    return info


def search(query: str) -> list[dict[str, Any]]:
    """Search by title. Returns AniList-shaped media dicts."""
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
    """Return airing status. info['status'] is an AiringStatus enum value."""
    try:
        return _normalize(anilist.get_airing(mal_id))
    except AniListUnavailable as exc:
        logger.info("AniList get_airing(%s) failed (%s); falling back to Jikan", mal_id, exc)
    try:
        return _normalize(jikan.get_airing(mal_id))
    except JikanUnavailable as exc:
        logger.error("Jikan get_airing(%s) also failed: %s", mal_id, exc)
        raise MetadataUnavailable(str(exc)) from exc
