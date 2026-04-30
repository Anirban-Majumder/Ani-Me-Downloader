"""Jikan v4 (unofficial MAL mirror) adapter.

Used as a fallback when AniList is unavailable. Output shapes mirror what
the AniList adapter returns so callers stay agnostic to the source.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None  # type: ignore[assignment]

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.jikan.moe/v4"
TIMEOUT = 10

_STATUS_MAP = {
    "Currently Airing": "RELEASING",
    "Finished Airing": "FINISHED",
    "Not yet aired": "NOT_YET_RELEASED",
}

_WEEKDAY_INDEX = {
    "Mondays": 0, "Tuesdays": 1, "Wednesdays": 2, "Thursdays": 3,
    "Fridays": 4, "Saturdays": 5, "Sundays": 6,
}


class JikanUnavailable(Exception):
    """Raised when Jikan cannot satisfy the request."""


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = requests.get(f"{API_URL}{path}", params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise JikanUnavailable(f"network error: {exc}") from exc
    if not response.ok:
        raise JikanUnavailable(
            f"HTTP {response.status_code}: {response.text[:200]}"
        )
    return response.json()


def _next_broadcast_unix(broadcast: dict[str, Any] | None) -> int:
    """Compute unix timestamp of the next broadcast slot, or 0 if unknown."""
    if not broadcast:
        return 0
    day = broadcast.get("day")
    time_str = broadcast.get("time")
    tz_str = broadcast.get("timezone") or "Asia/Tokyo"
    if not day or not time_str or ZoneInfo is None:
        return 0
    target_dow = _WEEKDAY_INDEX.get(day)
    if target_dow is None:
        return 0
    try:
        hour, minute = (int(part) for part in time_str.split(":")[:2])
        tz = ZoneInfo(tz_str)
        now = datetime.now(tz)
        days_ahead = (target_dow - now.weekday()) % 7
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0) \
            + timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
        return int(candidate.timestamp())
    except (ValueError, KeyError) as exc:
        logger.warning("Failed to compute broadcast time from %r: %s", broadcast, exc)
        return 0


def _adapt_search_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map a Jikan anime entry into the AniList media shape consumed by the UI."""
    images = item.get("images") or {}
    jpg = images.get("jpg") or {}
    cover = jpg.get("large_image_url") or jpg.get("image_url") or ""

    next_ep: dict[str, int] | None = None
    if item.get("airing"):
        next_at = _next_broadcast_unix(item.get("broadcast"))
        if next_at:
            next_ep = {"airingAt": next_at, "episode": 1}

    status = _STATUS_MAP.get(item.get("status", ""), "FINISHED")
    mal_id = item["mal_id"]

    return {
        # Both fields point at the same MAL ID; existing search code reads
        # `idMal` to populate the new primary key.
        "id": mal_id,
        "idMal": mal_id,
        "title": {
            "romaji": item.get("title") or "",
            "english": item.get("title_english") or item.get("title") or "",
        },
        "format": (item.get("type") or "").lower(),
        "status": status,
        "episodes": item.get("episodes"),
        "nextAiringEpisode": next_ep,
        "coverImage": {"extraLarge": cover},
    }


def search(query: str, limit: int = 25) -> list[dict[str, Any]]:
    """Search MAL via Jikan. Returns entries shaped like AniList media."""
    payload = _get("/anime", {"q": query, "limit": limit})
    return [_adapt_search_item(item) for item in payload.get("data") or []]


def get_airing(mal_id: int) -> dict[str, Any]:
    """Look up airing status by MAL ID. Same shape as ``anilist.get_airing``."""
    payload = _get(f"/anime/{int(mal_id)}")
    data = payload.get("data") or {}
    status_text = data.get("status", "")

    if status_text == "Currently Airing":
        return {
            "status": "RELEASING",
            "next_eta": _next_broadcast_unix(data.get("broadcast")),
            # Jikan does not expose a precise "last aired episode" counter.
            "last_aired_episode": None,
        }
    if status_text == "Not yet aired":
        return {"status": "NOT_YET_RELEASED", "next_eta": 0, "last_aired_episode": None}
    return {"status": "FINISHED", "next_eta": 0, "last_aired_episode": None}
