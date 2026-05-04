# coding: utf-8
"""Snapshot pattern: deep-copy animes, process, return for merge."""
import copy

from PyQt5.QtCore import QThread, pyqtSignal

from ..core.anime import Anime
from .anime_service import AnimeService


def _network_ok() -> bool:
    try:
        import requests
        requests.get("https://example.com/", timeout=5)
        return True
    except Exception:
        return False


class AnimeThread(QThread):
    """One pass per tick. Mutates a deep copy; coordinator merges by id."""
    finished_with = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, animes: list[Anime], service: AnimeService):
        super().__init__()
        self._animes = copy.deepcopy(animes)
        self._service = service

    def run(self) -> None:
        if not _network_ok():
            self.error.emit("There is something wrong with your Internet connection.")
            return
        for anime in self._animes:
            try:
                self._service.process(anime)
            except Exception as exc:
                print(f"Error processing anime {anime.name}: {exc}")
                self.error.emit(f"Error checking {anime.name}: {exc}")
        self.finished_with.emit(self._animes)
