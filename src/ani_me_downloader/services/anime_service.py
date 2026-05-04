# coding: utf-8
"""Per-anime workflow: refresh metadata, promote, search Nyaa, pick magnets."""
import time
from typing import Callable

from PyQt5.QtCore import QObject, pyqtSignal

from ..core.anime import AiringStatus, Anime, EpState, EpStatus
from ..core.episodes import episode_display_name
from ..core.identity import info_hash_from_magnet
from ..core.time_util import get_time_difference
from ..core.torrent import Torrent, TorrentStatus
from ..metadata.orchestrator import MetadataUnavailable, get_airing
from ..search.nyaa import NyaaResult, search_nyaa
from ..search.selector import select_torrent


class SearchFailed(Exception):
    """Nyaa search raised or returned no candidates after retries."""


class AnimeService(QObject):
    """Qt wrapper. Mutates an Anime in place via `process(anime)`."""
    info = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)
    selection = pyqtSignal(int, list)
    add_torrent = pyqtSignal(object)

    def __init__(self, *, use_proxy: Callable[[], bool]):
        super().__init__()
        self._use_proxy = use_proxy

    def process(self, anime: Anime) -> Anime:
        """Run the per-anime workflow once. Mutates `anime` and returns it."""
        print("-" * 80)
        print(f"Looking into {anime.name}")

        self._maybe_refresh_metadata(anime)

        if anime.status in (AiringStatus.NOT_YET_RELEASED, AiringStatus.HIATUS):
            return anime

        pending = anime.pending_eps()
        if not pending:
            return anime

        results: list[NyaaResult] | None = None
        for ep_index in pending:
            if results is None:
                results = self._search(anime)
                if not results:
                    self.error.emit(f"No torrent found for {anime.name}")
                    return anime

            magnet = self._pick(anime, ep_index, results)
            if magnet is None:
                if ep_index == 0:
                    self.selection.emit(anime.id, results)
                    self.error.emit("Could not auto-pick a batch torrent")
                else:
                    self.error.emit(
                        f"No matching torrent for {anime.name} ep {ep_index}"
                    )
                continue
            self._attach(anime, ep_index=ep_index, magnet=magnet)
        return anime

    def _maybe_refresh_metadata(self, anime: Anime) -> None:
        if not anime.needs_metadata_refresh:
            return
        if anime.next_eta and anime.next_eta > int(time.time()):
            d, h, m = get_time_difference(anime.next_eta)
            print(f"Next episode airing in about {d}d {h}h {m}m")
            return
        try:
            info = get_airing(anime.id)
        except MetadataUnavailable as exc:
            print(f"Could not refresh airing for {anime.name}: {exc}")
            self.error.emit(f"Could not check {anime.name}: source unavailable")
            return

        anime.status = info["status"]
        anime.next_eta = info.get("next_eta", 0)
        last = info.get("last_aired_episode")
        if last is not None:
            anime.last_aired_episode = last
        if anime.status is not AiringStatus.RELEASING:
            anime.last_aired_episode = anime.total_episodes
            anime.next_eta = 0
            self.info.emit(f"{anime.name} has finished airing!")

    def _search(self, anime: Anime) -> list[NyaaResult]:
        self.info.emit(f"Looking for {anime.name}...")
        self.info.emit("searching")
        try:
            primary = search_nyaa(anime.search_name or anime.name, use_proxy=self._use_proxy())
            extra: list[NyaaResult] = []
            if anime.search_name and anime.search_name != anime.name:
                extra = search_nyaa(anime.name, use_proxy=self._use_proxy())
            results = self._merge(primary, extra)
        except Exception as exc:
            self.error.emit("searching")
            raise SearchFailed(str(exc)) from exc
        self.error.emit("searching")
        results.sort(key=lambda r: r.seeds, reverse=True)
        print(f"Found {len(results)} torrents")
        return results

    @staticmethod
    def _merge(a: list[NyaaResult], b: list[NyaaResult]) -> list[NyaaResult]:
        seen: set[tuple] = set()
        out: list[NyaaResult] = []
        for r in (*a, *b):
            key = (r.title, r.magnet)
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    def _pick(self, anime: Anime, ep_index: int, results: list[NyaaResult]) -> str | None:
        episode = None if ep_index == 0 else ep_index
        return select_torrent(
            results,
            name=anime.name,
            search_name=anime.search_name or anime.name,
            season=anime.season,
            episode=episode,
        )

    def _attach(self, anime: Anime, *, ep_index: int, magnet: str) -> None:
        ih = info_hash_from_magnet(magnet)
        if not ih:
            self.error.emit(f"Picked magnet has no info_hash: {magnet[:60]}…")
            return
        is_batch = ep_index == 0
        new_state = EpStatus.BATCH_PENDING if is_batch else EpStatus.DOWNLOADING
        anime.episodes = [e for e in anime.episodes if e.ep != ep_index]
        anime.episodes.append(EpState(ep=ep_index, status=new_state, magnet=magnet))
        name = episode_display_name(anime, ep_index)
        torrent = Torrent(
            info_hash=ih,
            magnet=magnet,
            name=name,
            save_path=anime.output_dir,
            anime_ids={anime.id},
            desired_state=TorrentStatus.DOWNLOADING,
        )
        self.add_torrent.emit(torrent)
        self.success.emit(f"Download started {name}")
