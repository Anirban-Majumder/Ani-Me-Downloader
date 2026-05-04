# coding: utf-8
"""Search → resolve → confirm → emit add payload. All network off the GUI thread."""
import os
import re

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QListWidgetItem
from qfluentwidgets import MessageBox, SearchLineEdit, StateToolTip

from ..components.anime_dialog import AnimeDialog
from ..components.list_dialog import ListDialog
from ..config.config import cfg
from ..services.resolve_thread import AddCandidate, ResolveThread
from ..services.search_thread import SearchThread
from .base_interface import BaseInterface
from .style_sheet import StyleSheet


_NON_ALPHANUM = re.compile(r"[^\w\s]|_", re.UNICODE)


def _remove_non_alphanum(s: str) -> str:
    return _NON_ALPHANUM.sub("", s)


def _clean_title(title: str) -> str:
    """Strip 'Season ...' / 'Part ...' tails so search names match Nyaa releases."""
    if re.search(r"season", title, re.IGNORECASE):
        title = re.split(r"season", title, flags=re.IGNORECASE)[0]
    if re.search(r"part", title, re.IGNORECASE):
        title = re.split(r"part", title, flags=re.IGNORECASE)[0]
    return _remove_non_alphanum(title).strip()


class SearchInterface(BaseInterface):
    """Add-flow search UI. addSignal carries the new payload shape."""
    addSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.vBoxLayout.addSpacing(100)
        self.label = QLabel("Ani-Me  Downloader")
        self.label.setObjectName("title")
        self.vBoxLayout.addWidget(self.label, 0, Qt.AlignCenter)

        self.vBoxLayout.addSpacing(50)

        self.search_field = SearchLineEdit(self)
        self.search_field.setPlaceholderText("Enter the anime name")
        self.search_field.setFixedSize(400, 40)
        self.search_field.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.search_field, 0, Qt.AlignCenter)
        self.search_field.searchSignal.connect(self._on_search_clicked)
        self.search_field.clearSignal.connect(self._clear_line)
        self.search_field.returnPressed.connect(self._on_search_clicked)
        StyleSheet.SEARCH_INTERFACE.apply(self)

        self._search_thread: SearchThread | None = None
        self._resolve_thread: ResolveThread | None = None
        self._statebox: StateToolTip | None = None
        self._resolvebox: StateToolTip | None = None

    def _clear_line(self) -> None:
        self.search_field.clear()
        self.search_field.setPlaceholderText("Enter the anime name")

    def _on_search_clicked(self) -> None:
        query = self.search_field.text().strip()
        if not query:
            return
        self._statebox = StateToolTip("Searching", f"searching for {query}", self)
        self._statebox.move(int(self.width() / 2 - self._statebox.width() / 2), 10)
        self._statebox.show()

        self._search_thread = SearchThread(query)
        self._search_thread.searchFinished.connect(self._on_search_finished)
        self._search_thread.error.connect(self._on_search_error)
        self._search_thread.start()

    def _on_search_error(self, msg: str) -> None:
        if self._statebox:
            self._statebox.setState(True)
            self._statebox = None
        self._clear_line()
        MessageBox("Search failed", msg, self).exec_()

    def _on_search_finished(self, results: list) -> None:
        if self._statebox:
            self._statebox.setState(True)
            self._statebox = None
        self._clear_line()

        if not results:
            MessageBox(
                "No results found",
                "Try entering the proper name of the anime",
                self,
            ).exec_()
            return

        dialog = ListDialog("Search Results", "Choose the anime form the list:", self)
        for entry in results:
            item = QListWidgetItem(entry["title"]["romaji"])
            item.setData(Qt.UserRole, entry)
            dialog.list_view.addItem(item)
        if not dialog.exec_():
            return

        selected = dialog.list_view.currentItem().data(Qt.UserRole)
        if selected.get("status") == "NOT_YET_RELEASED":
            MessageBox(
                "Sorry this anime is not yet released",
                "Please try again later, when the anime is airing.",
                self,
            ).exec_()
            return

        self._resolvebox = StateToolTip("Resolving", "looking up watch URL", self)
        self._resolvebox.move(int(self.width() / 2 - self._resolvebox.width() / 2), 10)
        self._resolvebox.show()

        self._resolve_thread = ResolveThread(selected)
        self._resolve_thread.resolved.connect(self._on_resolved)
        self._resolve_thread.error.connect(self._on_resolve_error)
        self._resolve_thread.start()

    def _on_resolve_error(self, msg: str) -> None:
        if self._resolvebox:
            self._resolvebox.setState(True)
            self._resolvebox = None
        MessageBox("Could not resolve", msg, self).exec_()

    def _on_resolved(self, candidate: AddCandidate) -> None:
        if self._resolvebox:
            self._resolvebox.setState(True)
            self._resolvebox = None

        selected = candidate.selection
        anime_name = selected["title"]["romaji"]
        name = _remove_non_alphanum(anime_name)
        search_name = _clean_title(anime_name)
        selected["season"] = candidate.season
        selected["title"]["romaji"] = search_name

        dialog = AnimeDialog(selected, self)
        if not dialog.exec_():
            return

        search_name = dialog.title_label.text()
        total_episodes = dialog.episodes.value()
        season = dialog.season.value()
        from_ep = dialog.from_download.value()
        to_ep = dialog.to_download.value()
        download_type = dialog.download_type.currentText()
        status_str = dialog.status_combobox.currentText()
        airing = status_str == "RELEASING"
        if airing:
            last_aired = max(0, dialog.next_airing_episode.value() - 1)
        else:
            last_aired = total_episodes

        next_eta = (
            selected["nextAiringEpisode"]["airingAt"]
            if selected.get("nextAiringEpisode")
            else 0
        )
        output_dir = os.path.join(cfg.downloadFolder.value, name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        mal_id = selected.get("idMal") or selected.get("id") or 0
        if not mal_id:
            MessageBox(
                "Cannot add anime",
                "This entry has no MyAnimeList ID, which is required.",
                self,
            ).exec_()
            return

        if download_type == "Full":
            mode = "batch"
        elif download_type == "None":
            mode = "track_only"
            from_ep = 1
            to_ep = total_episodes
        else:
            mode = "episodes"

        payload = {
            "id": mal_id,
            "name": name,
            "search_name": search_name,
            "season": season,
            "format": (selected.get("format") or "unknown"),
            "img": selected["coverImage"]["extraLarge"],
            "watch_urls": candidate.watch_urls,
            "output_dir": output_dir,
            "status": status_str,
            "next_eta": next_eta,
            "last_aired_episode": last_aired,
            "total_episodes": total_episodes,
            "mode": mode,
            "from_ep": from_ep,
            "to_ep": to_ep,
        }
        self.addSignal.emit(payload)
