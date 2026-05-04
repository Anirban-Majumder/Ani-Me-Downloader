# coding: utf-8
"""Cover-image fetch + on-disk cache."""
import os

import requests
from PyQt5.QtGui import QPixmap

from ..config.paths import data_dir, get_r_path


def get_img(url: str) -> QPixmap:
    """Return a QPixmap for `url`, caching the bytes under data_dir/cache/."""
    cache_dir = os.path.join(data_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    last = url.split("/")[-1] if url else ""
    path = os.path.join(cache_dir, last) if last else ""
    try:
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap
        if url:
            data = requests.get(url).content
            pixmap = QPixmap()
            if pixmap.loadFromData(data) and path:
                pixmap.save(path)
                return pixmap
    except Exception as e:
        print(f"Error loading image: {e}")
    return QPixmap(get_r_path("logo.png"))
