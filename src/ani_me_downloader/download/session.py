# coding: utf-8
"""libtorrent session wrapper. No threads, no Qt, no queues."""
import ctypes
import os
import sys

from ..core.torrent import FilePriority, Torrent
from . import resume

print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"Executable: {sys.executable}")

# Windows: libtorrent wheel does not bundle OpenSSL. The .pyd imports fine but
# session/network init crashes when libssl/libcrypto are missing. Add the
# bundled DLL dir (populated by CI) to the search path before import.
if sys.platform == "win32":
    _here = os.path.dirname(os.path.abspath(__file__))
    _dll_dir = os.path.normpath(os.path.join(_here, "..", "resources", "dll_win"))
    if os.path.isdir(_dll_dir):
        try:
            os.add_dll_directory(_dll_dir)
            print(f"Added DLL search dir: {_dll_dir}")
        except Exception as e:
            print(f"add_dll_directory failed: {e}")
    else:
        print(f"DLL dir not found (dev run?): {_dll_dir}")

    print("Probing Windows native deps:")
    for _dll in (
        "vcruntime140.dll",
        "libcrypto-3-x64.dll", "libssl-3-x64.dll",
        "libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll",
    ):
        try:
            ctypes.CDLL(_dll)
            print(f"  {_dll}: OK")
        except OSError:
            print(f"  {_dll}: MISSING")

try:
    import libtorrent as lt
    print(f"libtorrent version: {lt.__version__}")
except ImportError as e:
    print(f"Failed to import libtorrent: {e}")
    lt = None
except Exception as e:
    print(f"Error loading libtorrent: {type(e).__name__}: {e}")
    lt = None


_LT_PRIORITY: dict[FilePriority, int] = {
    FilePriority.SKIP: 0,
    FilePriority.LOW: 1,
    FilePriority.NORMAL: 4,
    FilePriority.HIGH: 7,
}


def default_settings(max_concurrent_downloads: int) -> dict:
    """Reasonable libtorrent settings dict."""
    return {
        "listen_interfaces": "0.0.0.0:6881,[::]:6881",
        "enable_dht": True,
        "enable_lsd": True,
        "enable_natpmp": True,
        "enable_upnp": True,
        "announce_to_all_trackers": True,
        "announce_to_all_tiers": True,
        "connections_limit": 500,
        "download_rate_limit": 0,
        "upload_rate_limit": 0,
        "active_downloads": max_concurrent_downloads,
        "active_seeds": 10,
        "active_limit": max_concurrent_downloads + 10,
        "alert_mask": lt.alert.category_t.all_categories,
        "mixed_mode_algorithm": lt.bandwidth_mixed_algo_t.prefer_tcp,
        "enable_incoming_tcp": True,
        "enable_outgoing_tcp": True,
        "enable_incoming_utp": True,
        "enable_outgoing_utp": True,
        "strict_super_seeding": False,
        "dont_count_slow_torrents": False,
        "auto_manage_startup": 1,
        "auto_manage_interval": 5,
    }


class TorrentSession:
    """Thin wrapper around `lt.session`. Keyed by `info_hash`."""

    def __init__(self, settings: dict):
        if lt is None:
            raise RuntimeError(
                "libtorrent failed to load. Install Visual C++ Redistributable on Windows."
            )
        self._session = lt.session()
        self._session.apply_settings(settings)
        self._handles: dict[str, "lt.torrent_handle"] = {}
        self._torrents: dict[str, Torrent] = {}

    def add(self, t: Torrent):
        """Add a torrent. Re-applies fast-resume blob if present."""
        if t.info_hash in self._handles:
            print(f"Handle for {t.name} already exists, skipping")
            return self._handles[t.info_hash]

        params = lt.add_torrent_params()
        params.save_path = t.save_path
        params.url = t.magnet

        blob = resume.load_resume(t)
        if blob:
            try:
                params = lt.read_resume_data(blob)
                params.save_path = t.save_path
                params.url = t.magnet
                print(f"Loaded resume data for {t.name}")
            except Exception as e:
                print(f"Error loading resume data for {t.name}: {e}")

        params.flags |= lt.torrent_flags.auto_managed
        params.flags |= lt.torrent_flags.duplicate_is_error
        params.flags |= lt.torrent_flags.update_subscribe
        params.flags |= lt.torrent_flags.sequential_download

        handle = self._session.add_torrent(params)
        self._handles[t.info_hash] = handle
        self._torrents[t.info_hash] = t
        print(f"Added torrent {t.name}")
        return handle

    def remove(self, info_hash: str, *, delete_files: bool) -> bool:
        handle = self._handles.get(info_hash)
        if handle is None:
            return False
        t = self._torrents[info_hash]
        try:
            if handle.is_valid():
                handle.save_resume_data()
            self._session.remove_torrent(handle, int(delete_files))
            del self._handles[info_hash]
            del self._torrents[info_hash]
            resume.delete_resume(t)
            return True
        except Exception as e:
            print(f"Error removing torrent {t.name}: {e}")
            return False

    def pause(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle is None:
            return
        handle.unset_flags(lt.torrent_flags.auto_managed)
        handle.pause()

    def resume(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle is None:
            return
        handle.set_flags(lt.torrent_flags.auto_managed)
        handle.resume()

    def set_file_priority(self, info_hash: str, file_index: int, priority: FilePriority) -> bool:
        handle = self._handles.get(info_hash)
        if handle is None:
            return False
        try:
            priorities = list(handle.file_priorities())
            if not (0 <= file_index < len(priorities)):
                return False
            priorities[file_index] = _LT_PRIORITY[priority]
            handle.prioritize_files(priorities)
            return True
        except Exception as e:
            print(f"Error setting file priority: {e}")
            return False

    def force_recheck(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle is not None:
            handle.force_recheck()

    def request_resume_data_all(self) -> None:
        flags = lt.save_resume_flags_t.save_info_dict | lt.save_resume_flags_t.only_if_modified
        for h in list(self._handles.values()):
            try:
                if h.is_valid() and h.torrent_file():
                    h.save_resume_data(flags)
            except Exception:
                pass

    def pop_alerts(self) -> list:
        return self._session.pop_alerts()

    def handle_for(self, info_hash: str):
        return self._handles.get(info_hash)

    def torrent_for(self, info_hash: str) -> Torrent | None:
        return self._torrents.get(info_hash)

    def info_hash_for(self, handle) -> str | None:
        for h, hh in self._handles.items():
            if hh == handle:
                return h
        return None

    def all(self) -> list[tuple[str, Torrent, "lt.torrent_handle"]]:
        return [(h, self._torrents[h], self._handles[h]) for h in self._handles]

    def shutdown(self) -> None:
        self.request_resume_data_all()
