# coding: utf-8
"""Torrent JSON serialization, dedup-on-save, and repository."""
import logging
from pathlib import Path

from ..core.identity import info_hash_from_magnet
from ..core.torrent import Torrent, TorrentStatus
from .json_store import read_json, write_json_atomic

logger = logging.getLogger(__name__)


def torrent_to_json(t: Torrent) -> dict:
    return {
        "info_hash": t.info_hash,
        "magnet": t.magnet,
        "name": t.name,
        "save_path": t.save_path,
        "anime_ids": sorted(t.anime_ids),
        "desired_state": t.desired_state.value,
    }


def torrent_from_json(d: dict) -> Torrent:
    info_hash = d.get("info_hash") or info_hash_from_magnet(d.get("magnet", ""))
    if not info_hash:
        raise ValueError("Torrent missing both info_hash and parseable magnet")
    return Torrent(
        info_hash=info_hash,
        magnet=d["magnet"],
        name=d.get("name", ""),
        save_path=d["save_path"],
        anime_ids=set(d.get("anime_ids", [])),
        desired_state=TorrentStatus(d.get("desired_state", "downloading")),
    )


def torrents_dedup(torrents: list[Torrent]) -> list[Torrent]:
    """Collapse rows sharing an info_hash; merge anime_ids."""
    by_hash: dict[str, Torrent] = {}
    for t in torrents:
        existing = by_hash.get(t.info_hash)
        if existing is None:
            by_hash[t.info_hash] = t
        else:
            existing.anime_ids |= t.anime_ids
    return list(by_hash.values())


class TorrentRepository:
    """Loads and saves the torrent list. Sole writer of `torrent_file.json`."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self) -> list[Torrent]:
        items = read_json(self.path, default=[])
        out: list[Torrent] = []
        for d in items:
            try:
                out.append(torrent_from_json(d))
            except (KeyError, ValueError) as e:
                logger.warning("Skipping corrupt torrent row: %s", e)
        return out

    def save(self, torrents: list[Torrent]) -> None:
        write_json_atomic(
            self.path, [torrent_to_json(t) for t in torrents_dedup(torrents)]
        )
