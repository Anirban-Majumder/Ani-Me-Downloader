# coding: utf-8
"""Owns the libtorrent session via TorrentSession. Consumes typed commands."""
import math
import os
import queue
import time

from PyQt5.QtCore import QThread, pyqtSignal

from ..core.torrent import FilePriority, Torrent, TorrentStatus
from ..download import resume
from ..download.commands import (
    AddTorrent,
    Command,
    PauseTorrent,
    RemoveTorrent,
    ResumeTorrent,
    SetFilePriority,
)
from ..download.session import TorrentSession, default_settings, lt


_LT_TO_PRIORITY = {0: FilePriority.SKIP, 1: FilePriority.LOW, 4: FilePriority.NORMAL, 7: FilePriority.HIGH}


def _format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    return f"{round(size_bytes / math.pow(1024, i), 2)} {units[i]}"


class TorrentThread(QThread):
    """Long-lived. Wraps `TorrentSession`, dispatches typed commands."""
    progress = pyqtSignal(str, dict)
    completed = pyqtSignal(object)
    files_updated = pyqtSignal(str)
    error = pyqtSignal(str)
    exited = pyqtSignal(list)

    def __init__(
        self,
        torrents: list[Torrent],
        cmd_queue: "queue.Queue[Command]",
        max_concurrent_downloads: int,
    ):
        super().__init__()
        self._initial = torrents
        self._cmd_queue = cmd_queue
        self._max = max_concurrent_downloads
        self._stop = False
        self._recheck_done: set[str] = set()

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        if lt is None:
            self.error.emit(
                "libtorrent failed to load. Install Visual C++ Redistributable on Windows."
            )
            return
        try:
            sess = TorrentSession(default_settings(self._max))
        except Exception as exc:
            self.error.emit(str(exc))
            return

        self._enforce_concurrency_on_load()
        for t in self._initial:
            try:
                sess.add(t)
                self._apply_desired_state(sess, t)
            except Exception as exc:
                print(f"Error adding initial torrent {t.name}: {exc}")

        last_save = last_ui = time.time()
        while not self._stop:
            self._drain_commands(sess)
            self._drain_alerts(sess)
            now = time.time()
            if now - last_ui > 1:
                self._tick_ui(sess)
                last_ui = now
            if now - last_save > 60:
                sess.request_resume_data_all()
                last_save = now
            time.sleep(0.05)

        sess.request_resume_data_all()
        # Drain any remaining save_resume_data alerts before exiting.
        deadline = time.time() + 2
        while time.time() < deadline:
            self._drain_alerts(sess)
            time.sleep(0.05)
        self.exited.emit(self._initial)

    def _drain_commands(self, sess: TorrentSession) -> None:
        while not self._cmd_queue.empty():
            try:
                cmd = self._cmd_queue.get_nowait()
            except queue.Empty:
                return
            try:
                self._dispatch(sess, cmd)
            except Exception as exc:
                print(f"Error processing command {cmd!r}: {exc}")

    def _dispatch(self, sess: TorrentSession, cmd: Command) -> None:
        if isinstance(cmd, AddTorrent):
            sess.add(cmd.torrent)
            self._apply_desired_state(sess, cmd.torrent)
        elif isinstance(cmd, RemoveTorrent):
            sess.remove(cmd.info_hash, delete_files=cmd.delete_files)
        elif isinstance(cmd, PauseTorrent):
            sess.pause(cmd.info_hash)
            t = sess.torrent_for(cmd.info_hash)
            if t:
                t.desired_state = TorrentStatus.PAUSED
        elif isinstance(cmd, ResumeTorrent):
            sess.resume(cmd.info_hash)
            t = sess.torrent_for(cmd.info_hash)
            if t:
                t.desired_state = TorrentStatus.DOWNLOADING
        elif isinstance(cmd, SetFilePriority):
            sess.set_file_priority(cmd.info_hash, cmd.file_index, cmd.priority)

    @staticmethod
    def _apply_desired_state(sess: TorrentSession, t: Torrent) -> None:
        if t.desired_state is TorrentStatus.PAUSED:
            sess.pause(t.info_hash)
        else:
            sess.resume(t.info_hash)

    def _enforce_concurrency_on_load(self) -> None:
        active = 0
        for t in self._initial:
            if t.desired_state in (TorrentStatus.DOWNLOADING, TorrentStatus.QUEUED):
                if active < self._max:
                    t.desired_state = TorrentStatus.DOWNLOADING
                    active += 1
                else:
                    t.desired_state = TorrentStatus.QUEUED

    def _drain_alerts(self, sess: TorrentSession) -> None:
        for alert in sess.pop_alerts():
            try:
                self._handle_alert(sess, alert)
            except Exception as exc:
                print(f"Error handling alert: {exc}")

    def _handle_alert(self, sess: TorrentSession, alert) -> None:
        if isinstance(alert, lt.save_resume_data_alert):
            ih = sess.info_hash_for(alert.handle)
            if ih is None:
                return
            t = sess.torrent_for(ih)
            if t is None:
                return
            blob = lt.write_resume_data_buf(alert.params)
            resume.save_resume(t, blob)
            return

        if isinstance(alert, lt.save_resume_data_failed_alert):
            print(f"Save resume data failed: {alert.message()}")
            return

        if isinstance(alert, lt.metadata_received_alert):
            ih = sess.info_hash_for(alert.handle)
            if ih:
                self._refresh_files(sess, ih)
            return

        if isinstance(alert, lt.torrent_checked_alert):
            ih = sess.info_hash_for(alert.handle)
            if ih is None or ih not in self._recheck_done:
                return
            t = sess.torrent_for(ih)
            handle = sess.handle_for(ih)
            if t is None or handle is None:
                return
            s = handle.status()
            if s.is_seeding or s.progress >= 0.9999:
                self._mark_complete(sess, ih)
            else:
                print(f"Torrent {t.name} verification failed; resuming.")
                t.desired_state = TorrentStatus.DOWNLOADING
                sess.resume(ih)
                self._recheck_done.discard(ih)

    def _tick_ui(self, sess: TorrentSession) -> None:
        for ih, t, handle in list(sess.all()):
            try:
                if not handle.is_valid():
                    continue
                s = handle.status()
                t.progress = s.progress * 100.0
                t.dl_speed = int(s.download_rate)
                t.ul_speed = int(s.upload_rate)
                t.seeds = s.num_seeds
                t.peers = s.num_peers
                if s.download_rate > 0:
                    remaining = max(0, s.total_wanted - s.total_wanted_done)
                    t.eta = int(remaining / s.download_rate) if remaining > 0 else 0
                else:
                    t.eta = 0
                t.size_bytes = int(s.total_wanted)

                status = self._derive_status(t, s)
                if status is TorrentStatus.COMPLETED:
                    self._mark_complete(sess, ih)
                    continue

                if (
                    s.progress >= 0.9999
                    and status not in (TorrentStatus.VERIFYING, TorrentStatus.SEEDING, TorrentStatus.COMPLETED)
                    and ih not in self._recheck_done
                ):
                    print(f"[recheck] {t.name}")
                    self._recheck_done.add(ih)
                    sess.force_recheck(ih)
                    status = TorrentStatus.VERIFYING

                self.progress.emit(ih, self._snapshot(t, status))

                try:
                    if handle.torrent_file():
                        self._refresh_files(sess, ih)
                except Exception:
                    pass
            except Exception as exc:
                print(f"Error updating {t.name}: {exc}")

    @staticmethod
    def _derive_status(t: Torrent, s) -> TorrentStatus:
        if t.desired_state is TorrentStatus.PAUSED:
            return TorrentStatus.PAUSED
        if s.is_seeding or s.state == lt.torrent_status.finished or s.progress >= 0.99999:
            return TorrentStatus.COMPLETED
        if s.state == lt.torrent_status.checking_files:
            return TorrentStatus.VERIFYING
        if s.state == lt.torrent_status.queued_for_checking:
            return TorrentStatus.QUEUED
        if s.state == lt.torrent_status.checking_resume_data:
            return TorrentStatus.VERIFYING
        if s.state == lt.torrent_status.allocating:
            return TorrentStatus.DOWNLOADING
        if s.state == lt.torrent_status.seeding:
            return TorrentStatus.SEEDING
        if s.state == lt.torrent_status.downloading:
            return TorrentStatus.DOWNLOADING
        if s.paused and s.auto_managed:
            return TorrentStatus.QUEUED
        if s.paused:
            return TorrentStatus.PAUSED
        return TorrentStatus.DOWNLOADING

    def _mark_complete(self, sess: TorrentSession, ih: str) -> None:
        t = sess.torrent_for(ih)
        if t is None:
            return
        print(f"[complete] {t.name}")
        t.desired_state = TorrentStatus.COMPLETED
        sess.remove(ih, delete_files=False)
        self.completed.emit(t)

    @staticmethod
    def _snapshot(t: Torrent, status: TorrentStatus) -> dict:
        return {
            "name": t.name,
            "status": status.value,
            "progress": t.progress,
            "size": _format_size(t.size_bytes),
            "size_bytes": t.size_bytes,
            "dl_speed": t.dl_speed,
            "ul_speed": t.ul_speed,
            "eta": t.eta,
            "seeds": t.seeds,
            "peers": t.peers,
        }

    def _refresh_files(self, sess: TorrentSession, ih: str) -> None:
        handle = sess.handle_for(ih)
        t = sess.torrent_for(ih)
        if handle is None or t is None:
            return
        try:
            info = handle.torrent_file()
        except Exception:
            return
        if not info:
            return
        files = info.files()
        try:
            priorities = handle.get_file_priorities()
        except Exception:
            try:
                priorities = handle.file_priorities()
            except Exception:
                priorities = [4] * files.num_files()
        try:
            file_progress = handle.file_progress()
        except Exception:
            file_progress = [0] * files.num_files()

        from ..core.torrent import TorrentFile
        out: list[TorrentFile] = []
        for i in range(files.num_files()):
            size = files.file_size(i)
            done = file_progress[i] if i < len(file_progress) else 0
            prog = (done * 100.0 / size) if size > 0 else 0.0
            remaining = max(0, size - done)
            prio = _LT_TO_PRIORITY.get(priorities[i] if i < len(priorities) else 4, FilePriority.NORMAL)
            out.append(
                TorrentFile(
                    path=files.file_path(i),
                    size_bytes=size,
                    progress=min(100.0, prog),
                    priority=prio,
                    remaining_bytes=remaining,
                )
            )
        t.files = out
        self.files_updated.emit(ih)
