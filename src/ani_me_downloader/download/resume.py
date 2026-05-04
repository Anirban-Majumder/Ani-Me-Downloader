# coding: utf-8
"""Per-torrent fast-resume sidecar files."""
import os

from ..core.torrent import Torrent


def _path(t: Torrent) -> str:
    return os.path.join(t.save_path, f".{t.name}.fastresume")


def save_resume(t: Torrent, blob: bytes) -> None:
    path = _path(t)
    with open(path, "wb") as f:
        f.write(blob)
    print(f"Saved resume data to {path}")


def load_resume(t: Torrent) -> bytes | None:
    path = _path(t)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def delete_resume(t: Torrent) -> None:
    path = _path(t)
    if os.path.exists(path):
        os.remove(path)
