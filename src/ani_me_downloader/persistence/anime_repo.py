# coding: utf-8
"""Anime JSON serialization and repository."""
import logging
from pathlib import Path

from ..core.anime import Anime, AnimeFormat, AiringStatus, DownloadMode, EpState, EpStatus
from .json_store import read_json, write_json_atomic

logger = logging.getLogger(__name__)


# Stale statuses from pre-lazy schema. Drop on load (re-derived from
# last_aired_episode + presence in episodes list).
_DROPPED_EP_STATUSES = {"not_aired", "queued"}


def ep_to_json(e: EpState) -> dict:
    return {"ep": e.ep, "status": e.status.value, "magnet": e.magnet}


def ep_from_json(d: dict) -> EpState | None:
    raw = d.get("status")
    if raw in _DROPPED_EP_STATUSES:
        return None
    return EpState(
        ep=d["ep"],
        status=EpStatus(raw),
        magnet=d.get("magnet"),
    )


def anime_to_json(a: Anime) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "search_name": a.search_name,
        "season": a.season,
        "format": a.format.value,
        "output_dir": a.output_dir,
        "img": a.img,
        "watch_urls": dict(a.watch_urls),
        "status": a.status.value,
        "next_eta": a.next_eta,
        "last_aired_episode": a.last_aired_episode,
        "total_episodes": a.total_episodes,
        "download_mode": a.download_mode.value,
        "ep_from": a.ep_from,
        "ep_to": a.ep_to,
        "episodes": [ep_to_json(e) for e in a.episodes],
    }


def _parse_watch_urls(d: dict) -> dict[str, str]:
    """Read new `watch_urls` dict; fall back to legacy `watch_url` string."""
    raw = d.get("watch_urls")
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items() if v}
    legacy = d.get("watch_url")
    if isinstance(legacy, str) and legacy:
        return {"animekai": legacy}
    return {}


def _infer_download_mode(d: dict, eps: list[EpState]) -> DownloadMode:
    """Used when JSON predates `download_mode`. Heuristic from episode list."""
    raw = d.get("download_mode")
    if raw is not None:
        try:
            return DownloadMode(raw)
        except ValueError:
            pass
    if any(e.ep == 0 for e in eps):
        return DownloadMode.BATCH
    if eps and all(e.status is EpStatus.TRACK_ONLY for e in eps):
        return DownloadMode.TRACK_ONLY
    return DownloadMode.EPISODES


def anime_from_json(d: dict) -> Anime:
    raw_eps = d.get("episodes", [])
    eps: list[EpState] = []
    for row in raw_eps:
        ep = ep_from_json(row)
        if ep is not None:
            eps.append(ep)

    return Anime(
        id=d["id"],
        name=d["name"],
        search_name=d.get("search_name", d["name"]),
        season=d.get("season", 1),
        format=AnimeFormat(d.get("format", "unknown")),
        output_dir=d.get("output_dir", ""),
        img=d.get("img", ""),
        watch_urls=_parse_watch_urls(d),
        status=AiringStatus(d.get("status", "unknown")),
        next_eta=d.get("next_eta", 0),
        last_aired_episode=d.get("last_aired_episode", 0),
        total_episodes=d.get("total_episodes", 1),
        download_mode=_infer_download_mode(d, eps),
        ep_from=int(d.get("ep_from", 1)),
        ep_to=int(d.get("ep_to", 0)),
        episodes=eps,
    )


class AnimeRepository:
    """Loads and saves the anime list. Sole writer of `anime_file.json`."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self) -> list[Anime]:
        items = read_json(self.path, default=[])
        out: list[Anime] = []
        for d in items:
            try:
                out.append(anime_from_json(d))
            except (KeyError, ValueError) as e:
                logger.warning("Skipping corrupt anime row: %s", e)
        return out

    def save(self, animes: list[Anime]) -> None:
        write_json_atomic(self.path, [anime_to_json(a) for a in animes])
