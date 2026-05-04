# coding: utf-8
"""Filesystem paths used across the app."""
import os
from pathlib import Path

data_dir = os.path.join(os.path.expanduser("~"), ".Ani-Me-Downloader")
download_dir = os.path.join(os.path.expanduser("~"), "Downloads")


def get_r_path(path: str) -> str:
    """Resolve a path inside the bundled `resources/` dir."""
    return str(Path(__file__).resolve().parent.parent / "resources" / path)
