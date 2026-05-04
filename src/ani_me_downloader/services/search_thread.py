# coding: utf-8
"""AniList/Jikan search worker. Keeps GUI responsive during the add flow."""
from PyQt5.QtCore import QThread, pyqtSignal

from ..metadata.orchestrator import MetadataUnavailable, search


class SearchThread(QThread):
    """One-shot. Emits `searchFinished(list)` or `error(str)`."""
    searchFinished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            results = search(self.query)
        except MetadataUnavailable as exc:
            self.error.emit(f"Search providers unavailable: {exc}")
            return
        except Exception as exc:
            self.error.emit(f"Search failed: {exc}")
            return
        self.searchFinished.emit(results)
