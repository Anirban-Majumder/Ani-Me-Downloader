# coding: utf-8
"""Owns threads, command queue, and AppState writes."""
import os
import queue
import shutil
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from ..core.anime import AiringStatus, Anime, AnimeFormat, DownloadMode, EpState, EpStatus
from ..core.episodes import seed_episodes
from ..core.identity import info_hash_from_magnet, magnets_match
from ..core.torrent import Torrent, TorrentStatus
from ..download.commands import (
    AddTorrent,
    Command,
    PauseTorrent,
    RemoveTorrent,
    ResumeTorrent,
    SetFilePriority,
)
from ..metadata.orchestrator import MetadataUnavailable, get_airing
from ..search.nyaa import NyaaResult
from ..state.app_state import AppState
from .anime_service import AnimeService
from .anime_thread import AnimeThread
from .compression_thread import CompressionThread
from .run_thread import RunThread
from .torrent_thread import TorrentThread


class Coordinator(QObject):
    """High-level glue between view, AppState, and worker threads."""

    info = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)
    selection_needed = pyqtSignal(int, list)

    animes_changed = pyqtSignal()
    torrents_changed = pyqtSignal()
    torrent_progress = pyqtSignal(str, dict)
    torrent_files_updated = pyqtSignal(str)

    def __init__(
        self,
        state: AppState,
        *,
        use_proxy,
        tick_interval,
        max_concurrent,
        compress_videos=lambda: False,
        compress_use_cuda=lambda: True,
    ):
        super().__init__()
        self.state = state
        self.cmd_queue: "queue.Queue[Command]" = queue.Queue()
        self._max_concurrent = max_concurrent
        self._compress_videos = compress_videos
        self._compress_use_cuda = compress_use_cuda
        self._anime_service = AnimeService(use_proxy=use_proxy)
        self._wire_anime_service()
        self._torrent_thread: TorrentThread | None = None
        self._anime_thread: AnimeThread | None = None
        self._compression_thread: CompressionThread | None = None
        self._run_thread = RunThread(tick_interval)
        self._run_thread.tick.connect(self.start_anime_pass)
        self._run_thread.tick.connect(self.start_compression_pass)

    def _wire_anime_service(self) -> None:
        s = self._anime_service
        s.info.connect(self.info)
        s.error.connect(self.error)
        s.success.connect(self.success)
        s.selection.connect(self.selection_needed)
        s.add_torrent.connect(self._handle_service_torrent)

    def start(self) -> None:
        self.state.reconcile()
        self.state.save_torrents()
        self._start_torrent_thread()
        self._run_thread.start()

    def shutdown(self, *, timeout_seconds: int = 5) -> None:
        self._run_thread.stop()
        if self._torrent_thread:
            self._torrent_thread.stop()
            self._torrent_thread.wait(timeout_seconds * 1000)
        if self._anime_thread and self._anime_thread.isRunning():
            self._anime_thread.wait(timeout_seconds * 1000)
        if self._compression_thread and self._compression_thread.isRunning():
            self._compression_thread.wait(timeout_seconds * 1000)
        self.state.save_animes()
        self.state.save_torrents()

    def _start_torrent_thread(self) -> None:
        if self._torrent_thread and self._torrent_thread.isRunning():
            return
        self._torrent_thread = TorrentThread(
            self.state.torrents, self.cmd_queue, self._max_concurrent
        )
        self._torrent_thread.progress.connect(self.torrent_progress)
        self._torrent_thread.completed.connect(self._on_torrent_complete)
        self._torrent_thread.files_updated.connect(self.torrent_files_updated)
        self._torrent_thread.error.connect(self.error)
        self._torrent_thread.start()

    def add_anime(self, info: dict[str, Any]) -> None:
        """Build Anime from view payload, confirm airing, seed episodes."""
        try:
            mal_id = int(info["id"])
        except (KeyError, TypeError, ValueError):
            self.error.emit("Add failed: missing MAL id")
            return

        mode_raw = info.get("mode", "episodes")
        try:
            mode = DownloadMode(mode_raw)
        except ValueError:
            mode = DownloadMode.EPISODES
        from_ep = int(info.get("from_ep", 1))
        to_ep_raw = info.get("to_ep")
        ep_to = int(to_ep_raw) if to_ep_raw is not None else 0

        anime = Anime(
            id=mal_id,
            name=info.get("name", ""),
            search_name=info.get("search_name", info.get("name", "")),
            season=int(info.get("season", 1)),
            format=_to_format(info.get("format", "unknown")),
            output_dir=info.get("output_dir", ""),
            img=info.get("img", ""),
            watch_urls=dict(info.get("watch_urls") or {}),
            status=_to_status(info.get("status", "unknown")),
            next_eta=int(info.get("next_eta", 0)),
            last_aired_episode=int(info.get("last_aired_episode", 0)),
            total_episodes=int(info.get("total_episodes", 1)),
            download_mode=mode,
            ep_from=from_ep,
            ep_to=ep_to,
        )

        try:
            airing = get_airing(mal_id)
            anime.status = airing["status"]
            anime.next_eta = airing.get("next_eta", anime.next_eta)
            last = airing.get("last_aired_episode")
            if last is not None:
                anime.last_aired_episode = last
        except MetadataUnavailable as exc:
            self.error.emit(f"Metadata sources unavailable: {exc}")

        if anime.status is AiringStatus.UNKNOWN:
            anime.status = AiringStatus.FINISHED

        anime.episodes = seed_episodes(
            mode=mode_raw,
            total_episodes=anime.total_episodes,
            from_ep=from_ep,
            to_ep=to_ep_raw,
        )

        if anime.output_dir and not os.path.exists(anime.output_dir):
            os.makedirs(anime.output_dir, exist_ok=True)

        self.state.add_anime(anime)
        self.state.save_animes()
        self.animes_changed.emit()
        self.success.emit(f"Added {anime.name}")
        self.start_anime_pass()

    def remove_anime(self, id: int) -> None:
        anime = self.state.remove_anime(id)
        if anime is None:
            return
        for t in list(self.state.torrents):
            if id in t.anime_ids:
                t.anime_ids.discard(id)
                if not t.anime_ids:
                    self.cmd_queue.put(RemoveTorrent(t.info_hash, delete_files=True))
                    self.state.remove_torrent(t.info_hash)
        try:
            if anime.output_dir:
                shutil.rmtree(anime.output_dir)
        except Exception as exc:
            self.error.emit(
                f"Could not delete folder {anime.output_dir}: something is using it ({exc})"
            )
        self.state.save_animes()
        self.state.save_torrents()
        self.animes_changed.emit()
        self.torrents_changed.emit()

    def start_anime_pass(self) -> None:
        if not self.state.animes:
            self.info.emit("Add Anime by Searching for it.")
            return
        if self._anime_thread and self._anime_thread.isRunning():
            return
        self._anime_thread = AnimeThread(self.state.animes, self._anime_service)
        self._anime_thread.finished_with.connect(self._on_anime_pass_done)
        self._anime_thread.error.connect(self.error)
        self._anime_thread.start()

    def start_compression_pass(self) -> None:
        if not self._compress_videos():
            return
        if self._compression_thread and self._compression_thread.isRunning():
            return
        self._compression_thread = CompressionThread(
            self.state.animes, self.state.torrents, self._compress_use_cuda()
        )
        self._compression_thread.info.connect(self.info)
        self._compression_thread.error.connect(self.error)
        self._compression_thread.start()

    def _on_anime_pass_done(self, returned: list[Anime]) -> None:
        by_id = {a.id: a for a in returned}
        merged: list[Anime] = []
        for current in self.state.animes:
            updated = by_id.get(current.id)
            merged.append(_merge_anime(current, updated) if updated else current)
        self.state.animes = merged
        self.state.save_animes()
        self.animes_changed.emit()

    def _handle_service_torrent(self, t: Torrent) -> None:
        if not t.info_hash:
            ih = info_hash_from_magnet(t.magnet)
            if not ih:
                return
            t.info_hash = ih
        existing = self.state.get_torrent(t.info_hash)
        canonical = self.state.add_torrent(t)
        self.state.save_torrents()
        self.torrents_changed.emit()
        if existing is None:
            self.cmd_queue.put(AddTorrent(canonical))

    def _on_torrent_complete(self, t: Torrent) -> None:
        canonical = self.state.get_torrent(t.info_hash) or t
        for aid in list(canonical.anime_ids):
            anime = self.state.get_anime(aid)
            if anime is None:
                continue
            for ep in anime.episodes:
                if not ep.magnet or not magnets_match(ep.magnet, canonical.magnet):
                    continue
                if ep.status is EpStatus.BATCH_PENDING:
                    ep.status = EpStatus.BATCH_DONE
                else:
                    ep.status = EpStatus.DONE
                ep.magnet = None
                self.success.emit(
                    f"Episode {ep.ep if ep.ep else 'batch'} of {anime.name} completed"
                )
        self.state.remove_torrent(canonical.info_hash)
        self.state.save_animes()
        self.state.save_torrents()
        self.animes_changed.emit()
        self.torrents_changed.emit()

    def toggle_pause(self, info_hash: str) -> None:
        t = self.state.get_torrent(info_hash)
        if t is None:
            return
        if t.desired_state is TorrentStatus.PAUSED:
            self.cmd_queue.put(ResumeTorrent(info_hash))
            t.desired_state = TorrentStatus.DOWNLOADING
            self.success.emit(f"Resumed {t.name}")
        else:
            self.cmd_queue.put(PauseTorrent(info_hash))
            t.desired_state = TorrentStatus.PAUSED
            self.success.emit(f"Paused {t.name}")

    def delete_torrent(self, info_hash: str, *, delete_files: bool = False) -> None:
        t = self.state.remove_torrent(info_hash)
        if t is None:
            return
        self.cmd_queue.put(RemoveTorrent(info_hash, delete_files=delete_files))
        self.state.save_torrents()
        self.torrents_changed.emit()
        self.success.emit(f"Deleted {t.name}{' with files' if delete_files else ''}")

    def change_file_priority(self, info_hash: str, file_index: int, priority) -> None:
        self.cmd_queue.put(SetFilePriority(info_hash, file_index, priority))

    def receive_torrent_choice(self, anime_id: int, result: NyaaResult) -> None:
        anime = self.state.get_anime(anime_id)
        if anime is None:
            return
        ih = info_hash_from_magnet(result.magnet)
        if not ih:
            self.error.emit("Selected magnet has no info_hash")
            return
        from ..core.episodes import episode_display_name
        pending = anime.pending_eps()
        if not pending:
            return
        ep_index = pending[0]
        is_batch = ep_index == 0
        new_state = EpStatus.BATCH_PENDING if is_batch else EpStatus.DOWNLOADING
        anime.episodes = [e for e in anime.episodes if e.ep != ep_index]
        anime.episodes.append(EpState(ep=ep_index, status=new_state, magnet=result.magnet))
        t = Torrent(
            info_hash=ih,
            magnet=result.magnet,
            name=episode_display_name(anime, ep_index),
            save_path=anime.output_dir,
            anime_ids={anime.id},
            desired_state=TorrentStatus.DOWNLOADING,
        )
        self._handle_service_torrent(t)
        self.state.save_animes()
        self.animes_changed.emit()


def _to_status(value: Any) -> AiringStatus:
    if isinstance(value, AiringStatus):
        return value
    if isinstance(value, str):
        try:
            return AiringStatus(value.lower())
        except ValueError:
            mapping = {
                "RELEASING": AiringStatus.RELEASING,
                "FINISHED": AiringStatus.FINISHED,
                "NOT_YET_RELEASED": AiringStatus.NOT_YET_RELEASED,
                "HIATUS": AiringStatus.HIATUS,
                "CANCELLED": AiringStatus.CANCELLED,
            }
            return mapping.get(value, AiringStatus.UNKNOWN)
    return AiringStatus.UNKNOWN


def _to_format(value: Any) -> AnimeFormat:
    if isinstance(value, AnimeFormat):
        return value
    if isinstance(value, str):
        try:
            return AnimeFormat(value.lower())
        except ValueError:
            return AnimeFormat.UNKNOWN
    return AnimeFormat.UNKNOWN


_TERMINAL_EP = {EpStatus.DONE, EpStatus.BATCH_DONE, EpStatus.TRACK_ONLY}


def _merge_anime(current: Anime, updated: Anime) -> Anime:
    """GUI-side wins for user-edited fields and terminal episode states; thread wins otherwise."""
    current.status = updated.status
    current.next_eta = updated.next_eta
    current.last_aired_episode = updated.last_aired_episode
    current.total_episodes = updated.total_episodes

    by_ep = {ep.ep: ep for ep in updated.episodes}
    merged_eps = []
    for cur_ep in current.episodes:
        thread_ep = by_ep.get(cur_ep.ep)
        if thread_ep is None:
            merged_eps.append(cur_ep)
            continue
        if cur_ep.status in _TERMINAL_EP:
            merged_eps.append(cur_ep)
        else:
            merged_eps.append(thread_ep)
    seen = {ep.ep for ep in merged_eps}
    for thread_ep in updated.episodes:
        if thread_ep.ep not in seen:
            merged_eps.append(thread_ep)
    current.episodes = merged_eps
    return current
