# coding: utf-8
"""Resolve an AniList selection: fetch watch URLs + season off the GUI thread."""
from dataclasses import dataclass, field
from typing import Any

from PyQt5.QtCore import QThread, pyqtSignal

from ..metadata.watch_lookup import get_season, get_watch_urls


@dataclass
class AddCandidate:
    selection: dict[str, Any]
    watch_urls: dict[str, str] = field(default_factory=dict)
    season: int = 1


class ResolveThread(QThread):
    """One-shot. Emits `resolved(AddCandidate)` or `error(str)`."""
    resolved = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, selection: dict[str, Any]):
        super().__init__()
        self.selection = selection

    def run(self) -> None:
        try:
            title = self.selection["title"]["romaji"]
            urls = get_watch_urls(title)
            season = get_season(urls.get("animekai", ""))
        except Exception as exc:
            self.error.emit(f"Could not resolve watch URLs: {exc}")
            return
        self.resolved.emit(
            AddCandidate(selection=self.selection, watch_urls=urls, season=season)
        )
