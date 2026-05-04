# coding: utf-8
"""AniList GraphQL adapter, keyed by MAL ID."""
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_URL = "https://graphql.anilist.co"
TIMEOUT = 10
_DISABLED_MARKERS = ("temporarily disabled", "severe stability")

LIST_QUERY = """
query ($search: String) {
  Page {
    media(search: $search, type: ANIME) {
      id
      idMal
      title { romaji english }
      format
      status
      episodes
      nextAiringEpisode { episode airingAt }
      coverImage { extraLarge }
    }
  }
}
"""

AIRING_QUERY = """
query ($idMal: Int) {
  Media(idMal: $idMal, type: ANIME) {
    id
    idMal
    status
    nextAiringEpisode { airingAt episode }
  }
}
"""


class AniListUnavailable(Exception):
    """Transport, HTTP, or upstream-disabled failure."""


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
        raise AniListUnavailable(f"HTTP {response.status_code}: {response.text[:200]}")

    payload = response.json()
    if payload.get("errors"):
        message = payload["errors"][0].get("message", "unknown GraphQL error")
        raise AniListUnavailable(f"GraphQL error: {message}")
    return payload["data"]


def search(query: str) -> list[dict[str, Any]]:
    """Search AniList by title. Returns AniList media dicts (include `idMal`)."""
    data = _post(LIST_QUERY, {"search": query})
    return (data.get("Page") or {}).get("media") or []


def get_airing(mal_id: int) -> dict[str, Any]:
    """Look up airing status by MAL ID. UPPERCASE status string."""
    data = _post(AIRING_QUERY, {"idMal": int(mal_id)})
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
