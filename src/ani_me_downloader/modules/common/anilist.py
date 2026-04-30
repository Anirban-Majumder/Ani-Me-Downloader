"""AniList GraphQL adapter.

Thin wrapper around the AniList v2 GraphQL endpoint. All lookups are keyed
by MAL ID (`idMal`) so the rest of the application can stay on a single
identifier scheme even when the upstream service changes.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from .constants import Constants

logger = logging.getLogger(__name__)

API_URL = Constants.api_url
TIMEOUT = 10
_DISABLED_MARKERS = ("temporarily disabled", "severe stability")


class AniListUnavailable(Exception):
    """Raised when the AniList API cannot satisfy the request.

    Covers transport failures, HTTP errors, and the upstream-disabled
    response that AniList currently serves on prolonged outages.
    """


def _post(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(
            API_URL,
            json={"query": query, "variables": variables},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise AniListUnavailable(f"network error: {exc}") from exc

    body_lower = (response.text or "").lower()
    if response.status_code == 403 and any(m in body_lower for m in _DISABLED_MARKERS):
        raise AniListUnavailable("AniList API is currently disabled by upstream")

    if not response.ok:
        raise AniListUnavailable(
            f"HTTP {response.status_code}: {response.text[:200]}"
        )

    payload = response.json()
    if payload.get("errors"):
        message = payload["errors"][0].get("message", "unknown GraphQL error")
        raise AniListUnavailable(f"GraphQL error: {message}")
    return payload["data"]


def search(query: str) -> list[dict[str, Any]]:
    """Search AniList by title. Returns AniList media dicts (include `idMal`)."""
    data = _post(Constants.list_query, {"search": query})
    media = (data.get("Page") or {}).get("media") or []
    return media


def get_airing(mal_id: int) -> dict[str, Any]:
    """Look up airing status by MAL ID.

    Returns a normalised dict::

        {"status": "RELEASING" | "FINISHED" | ...,
         "next_eta": int (unix seconds, 0 if unknown),
         "last_aired_episode": int | None}
    """
    data = _post(Constants.airing_query, {"idMal": int(mal_id)})
    media = data.get("Media")
    if not media:
        raise AniListUnavailable(f"no Media for idMal={mal_id}")

    status = media.get("status") or "FINISHED"
    next_ep = media.get("nextAiringEpisode")
    if next_ep:
        return {
            "status": status,
            "next_eta": int(next_ep["airingAt"]),
            "last_aired_episode": int(next_ep["episode"]) - 1,
        }
    return {"status": status, "next_eta": 0, "last_aired_episode": None}
