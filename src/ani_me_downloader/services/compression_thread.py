# coding: utf-8
"""Background AV1 re-encode pass over downloaded episodes.

Mirrors the standalone vid_com.py script. Triggered each tick when
`cfg.compressVideos` is enabled and ffmpeg is on PATH. Uses NVENC when
`cfg.compressUseCuda` is enabled and `av1_nvenc` is available; falls
back to libsvtav1 (CPU)."""
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt5.QtCore import QThread, pyqtSignal

from ..core.anime import Anime
from ..core.torrent import Torrent

COMPRESSED_KEYWORDS = ("x265", "hevc", "av1")
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".webm", ".flv"}
POOL_SIZE_CUDA = 8
POOL_SIZE_CPU = 1


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def nvenc_av1_available() -> bool:
    if not ffmpeg_available():
        return False
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return False
    return "av1_nvenc" in (out.stdout or "")


def _is_compressed(filename: str) -> bool:
    n = filename.lower()
    return any(k in n for k in COMPRESSED_KEYWORDS)


def _build_command(input_file: str, output_file: str, use_cuda: bool) -> list[str]:
    if use_cuda:
        return [
            "ffmpeg",
            "-hwaccel", "cuda",
            "-i", input_file,
            "-c:v", "av1_nvenc",
            "-preset", "p7",
            "-tune", "hq",
            "-cq", "22",
            "-c:a", "copy",
            "-c:s", "copy",
            "-map", "0",
            "-y",
            output_file,
        ]
    return [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libsvtav1",
        "-preset", "6",
        "-crf", "30",
        "-c:a", "copy",
        "-c:s", "copy",
        "-map", "0",
        "-y",
        output_file,
    ]


def _encode(task, use_cuda):
    input_file, output_file = task
    cmd = _build_command(input_file, output_file, use_cuda)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        try:
            os.remove(input_file)
        except OSError:
            pass
        return (True, input_file, None)
    except subprocess.CalledProcessError as e:
        return (False, input_file, (e.stderr or str(e)).strip().splitlines()[-1] if (e.stderr or str(e)) else "")
    except Exception as e:
        return (False, input_file, str(e))


def _collect_in_progress(torrents: list[Torrent]) -> set[str]:
    paths: set[str] = set()
    for t in torrents:
        if not t.save_path:
            continue
        for f in t.files:
            paths.add(os.path.normpath(os.path.join(t.save_path, f.path)))
    return paths


def _collect_tasks(animes: list[Anime], in_progress: set[str]) -> list[tuple[str, str]]:
    tasks: list[tuple[str, str]] = []
    for anime in animes:
        out = anime.output_dir
        if not out or not os.path.isdir(out):
            continue
        for root, _dirs, files in os.walk(out):
            for fn in files:
                if os.path.splitext(fn)[1].lower() not in VIDEO_EXTENSIONS:
                    continue
                full = os.path.normpath(os.path.join(root, fn))
                if full in in_progress:
                    continue
                if _is_compressed(fn):
                    continue
                name_no_ext, ext = os.path.splitext(fn)
                out_path = os.path.join(root, f"{name_no_ext}_AV1{ext}")
                if os.path.exists(out_path):
                    continue
                tasks.append((full, out_path))
    return tasks


class CompressionThread(QThread):
    info = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, animes: list[Anime], torrents: list[Torrent], use_cuda: bool):
        super().__init__()
        self._animes = list(animes)
        self._torrents = list(torrents)
        self._use_cuda = use_cuda

    def run(self) -> None:
        ffmpeg_ok = ffmpeg_available()
        nvenc_ok = nvenc_av1_available() if ffmpeg_ok else False
        print(
            f"[compress] detect: ffmpeg={ffmpeg_ok} av1_nvenc={nvenc_ok} "
            f"prefer_cuda={self._use_cuda}"
        )

        if not ffmpeg_ok:
            print("[compress] skip: ffmpeg not in PATH")
            self.error.emit("Compression skipped: ffmpeg not found in PATH.")
            return

        cuda = self._use_cuda and nvenc_ok
        if self._use_cuda and not cuda:
            self.info.emit("av1_nvenc unavailable; falling back to CPU encoder.")

        encoder = "NVENC (av1_nvenc)" if cuda else "CPU (libsvtav1)"
        pool_size = POOL_SIZE_CUDA if cuda else POOL_SIZE_CPU
        print(f"[compress] using: {encoder}, pool_size={pool_size}")

        in_progress = _collect_in_progress(self._torrents)
        tasks = _collect_tasks(self._animes, in_progress)
        if not tasks:
            print("[compress] no files to compress")
            return

        print(f"[compress] queued {len(tasks)} file(s)")
        self.info.emit(f"Compressing {len(tasks)} file(s) with {encoder}...")
        with ThreadPoolExecutor(max_workers=pool_size) as pool:
            futures = [pool.submit(_encode, t, cuda) for t in tasks]
            for fut in as_completed(futures):
                ok, inp, err = fut.result()
                base = os.path.basename(inp)
                if ok:
                    print(f"[compress] done: {base}")
                    self.info.emit(f"Compressed: {base}")
                else:
                    print(f"[compress] fail: {base}: {err}")
                    self.error.emit(f"Compress failed {base}: {err}")
