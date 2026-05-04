# coding: utf-8
"""MAL list-status editor dialog with anime info + episode-grid launcher."""
import re

from PyQt5.QtCore import QEvent, Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)
from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    PrimaryToolButton,
    SpinBox,
    isDarkTheme,
)
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox

from ..view.image_cache import get_img
from .episode_grid_dialog import EpisodeGridDialog


class _MalDetailsThread(QThread):
    """Fetch MAL details off the GUI thread."""
    loaded = pyqtSignal(dict, str)

    def __init__(self, anime_id, parent=None):
        super().__init__(parent)
        self.anime_id = anime_id

    def run(self):
        try:
            from ..metadata.mal import get_anime_details
            data = get_anime_details(self.anime_id)
            self.loaded.emit(data or {}, "")
        except Exception as e:
            self.loaded.emit({}, str(e))


class SyncDialog(MaskDialogBase, Ui_MessageBox):
    """Update an anime's MAL list status (status / score / watched)."""
    _SYN_MAX_CHARS = 360

    def __init__(self, anime, parent=None, coordinator=None):
        super().__init__(parent)
        self._setUpUi(f"Anime Info — {anime.name}", "", self.widget)
        self.yesButton.setText("Update")
        if hasattr(self, "contentLabel") and self.contentLabel is not None:
            self.contentLabel.hide()

        self.anime = anime
        self.anime_id = anime.id
        self.coordinator = coordinator
        self.img_size = (180, 260)
        self._details_thread = None

        if isDarkTheme():
            self._fg, self._fg_dim = "#e6e6e6", "#a8a8a8"
        else:
            self._fg, self._fg_dim = "#1a1a1a", "#606060"

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)

        self.message_box_layout = QHBoxLayout()
        self.message_box_layout.setContentsMargins(24, 0, 24, 0)
        self.message_box_layout.setSpacing(16)
        self.textLayout.setContentsMargins(24, 20, 24, 8)
        self.textLayout.setSpacing(0)
        self.vBoxLayout.setSpacing(8)
        self.vBoxLayout.insertLayout(1, self.message_box_layout)

        self.cover_image_label = QLabel()
        self.cover_image_label.setFixedSize(*self.img_size)
        self.load_img(anime.img, self.cover_image_label)
        self.message_box_layout.addWidget(self.cover_image_label, 0, Qt.AlignTop)

        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        self.message_box_layout.addLayout(right_col, 1)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_label = QLabel(anime.name)
        self.title_label.setStyleSheet(f"color: {self._fg}; font-size: 16px; font-weight: 600;")
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, 1)

        self.episodes_btn = PrimaryToolButton(FluentIcon.DOWNLOAD)
        self.episodes_btn.setToolTip("Manage episodes")
        self.episodes_btn.setFixedSize(30, 30)
        self.episodes_btn.clicked.connect(self._open_episode_grid)
        title_row.addWidget(self.episodes_btn, 0, Qt.AlignTop)

        mal_url = f"https://myanimelist.net/anime/{self.anime_id}"
        self.open_mal_btn = PrimaryToolButton(FluentIcon.LINK)
        self.open_mal_btn.setToolTip("Open on MyAnimeList")
        self.open_mal_btn.setFixedSize(30, 30)
        self.open_mal_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(mal_url)))
        title_row.addWidget(self.open_mal_btn, 0, Qt.AlignTop)
        right_col.addLayout(title_row)

        self.meta_label = QLabel("Loading details…")
        self.meta_label.setStyleSheet(f"color: {self._fg_dim}; font-size: 12px;")
        self.meta_label.setWordWrap(True)
        right_col.addWidget(self.meta_label)

        self.aired_label = QLabel("")
        self.studios_label = QLabel("")
        self.genres_label = QLabel("")
        for lbl in (self.aired_label, self.studios_label, self.genres_label):
            lbl.setStyleSheet(f"color: {self._fg}; font-size: 12px;")
            lbl.setWordWrap(True)
            right_col.addWidget(lbl)

        right_col.addSpacing(4)
        self.synopsis = QLabel("Loading synopsis…")
        self.synopsis.setStyleSheet(f"color: {self._fg}; font-size: 12px;")
        self.synopsis.setWordWrap(True)
        self.synopsis.setMinimumWidth(420)
        self.synopsis.setMaximumHeight(120)
        self.synopsis.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.synopsis.setTextInteractionFlags(Qt.TextSelectableByMouse)
        right_col.addWidget(self.synopsis)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        right_col.addWidget(sep)

        form_row = QHBoxLayout()
        form_row.setSpacing(10)
        form_row.setContentsMargins(0, 8, 0, 16)

        def _flabel(text):
            l = QLabel(text)
            l.setStyleSheet(f"color: {self._fg_dim}; font-size: 11px;")
            return l

        form_row.addWidget(_flabel("Status"))
        self.status_combobox = ComboBox(self)
        self.status_combobox.addItems(
            ["watching", "completed", "on_hold", "dropped", "plan_to_watch"]
        )
        self.status_combobox.setCurrentText("completed")
        self.status_combobox.setMinimumWidth(130)
        form_row.addWidget(self.status_combobox)

        form_row.addSpacing(8)
        form_row.addWidget(_flabel("Score"))
        self.score_spinbox = SpinBox(self)
        self.score_spinbox.setRange(0, 10)
        self.score_spinbox.setValue(0)
        self.score_spinbox.setMinimumWidth(110)
        form_row.addWidget(self.score_spinbox)

        form_row.addSpacing(8)
        form_row.addWidget(_flabel("Episodes"))
        self.watched_episodes = SpinBox(self)
        self.watched_episodes.setRange(0, max(1, anime.total_episodes))
        self.watched_episodes.setValue(anime.total_episodes)
        self.watched_episodes.setMinimumWidth(110)
        form_row.addWidget(self.watched_episodes)

        form_row.addStretch()
        right_col.addLayout(form_row)

        self._details_thread = _MalDetailsThread(self.anime_id, self)
        self._details_thread.loaded.connect(self._on_details_loaded)
        self._details_thread.start()

    def _open_episode_grid(self):
        dlg = EpisodeGridDialog(self.anime, self, coordinator=self.coordinator)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        dlg.exec_()

    @staticmethod
    def _clean_synopsis(s):
        if not s:
            return ""
        s = s.strip()
        pattern = re.compile(
            r"\s*(?:\[[^\]]*\]|\([^)]*?(?:Source|Written by)[^)]*\))\s*$",
            re.IGNORECASE,
        )
        prev = None
        while prev != s:
            prev = s
            s = pattern.sub("", s).rstrip()
        return s.strip()

    @classmethod
    def _truncate(cls, s, n=None):
        n = n or cls._SYN_MAX_CHARS
        if len(s) <= n:
            return s
        cut = s.rfind(" ", 0, n)
        if cut == -1:
            cut = n
        return s[:cut].rstrip(" ,.;:!?-—") + "…"

    def _on_details_loaded(self, data, err):
        if err or not data:
            self.synopsis.setText(
                "Could not load details from MyAnimeList." + (f"\n({err})" if err else "")
            )
            self.meta_label.setText("—")
            return

        if data.get("title"):
            self.title_label.setText(data["title"])

        bits = []
        if data.get("mean") is not None:
            bits.append(f"⭐ {data['mean']}")
        if data.get("rank"):
            bits.append(f"#{data['rank']}")
        if data.get("popularity"):
            bits.append(f"Pop #{data['popularity']}")
        if data.get("media_type"):
            bits.append(str(data["media_type"]).upper())
        if data.get("num_episodes"):
            bits.append(f"{data['num_episodes']} ep")
        if data.get("status"):
            bits.append(str(data["status"]).replace("_", " ").title())
        self.meta_label.setText(" · ".join(bits) if bits else "")

        start = data.get("start_date", "")
        end = data.get("end_date", "")
        if start or end:
            self.aired_label.setText(f"Aired: {start or '?'} → {end or 'ongoing'}")

        studios = data.get("studios") or []
        if studios:
            self.studios_label.setText(
                "Studios: " + ", ".join(s.get("name", "") for s in studios)
            )

        genres = data.get("genres") or []
        if genres:
            self.genres_label.setText(
                "Genres: " + ", ".join(g.get("name", "") for g in genres)
            )

        synopsis = self._clean_synopsis(data.get("synopsis") or "") or "(no synopsis available)"
        self.synopsis.setText(self._truncate(synopsis))

        mls = data.get("my_list_status") or {}
        if mls.get("status"):
            idx = self.status_combobox.findText(mls["status"])
            if idx >= 0:
                self.status_combobox.setCurrentIndex(idx)
        if mls.get("score") is not None:
            self.score_spinbox.setValue(int(mls["score"]))
        if mls.get("num_episodes_watched") is not None:
            self.watched_episodes.setValue(int(mls["num_episodes_watched"]))

    def closeEvent(self, event):
        if self._details_thread and self._details_thread.isRunning():
            self._details_thread.quit()
            self._details_thread.wait(2000)
        super().closeEvent(event)

    def load_img(self, url, label):
        pixmap = get_img(url)
        scaled = pixmap.scaled(*self.img_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window() and e.type() == QEvent.Resize:
            self._adjustText()
        return super().eventFilter(obj, e)

    def get_form_data(self):
        return {
            "anime_id": self.anime_id,
            "status": self.status_combobox.currentText(),
            "score": self.score_spinbox.value(),
            "num_watched_episodes": self.watched_episodes.value(),
        }
