import re

from PyQt5.QtCore import Qt, QEvent, QThread, pyqtSignal, QUrl
from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QPainter, QPen, QColor, QDesktopServices
from PyQt5.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QStyleOptionViewItem, QFormLayout,
    QFrame
)
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox
from qfluentwidgets import (
    ListWidget, LineEdit, SpinBox, ComboBox, ListItemDelegate, isDarkTheme,
    PrimaryToolButton, FluentIcon
)

from ..common.utils import get_img
from ..common.config import cfg


class CustomListItemDelegate(ListItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        super().paint(painter, option, index)
        painter.save()
        painter.setPen(QPen(QColor(cfg.themeColor.value.name())))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()


class ListDialog(MaskDialogBase, Ui_MessageBox):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent)
        self._setUpUi(title, content, self.widget)

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)
        self.message_box_layout = QVBoxLayout()
        self.vBoxLayout.insertLayout(1, self.message_box_layout)

        self.list_view = ListWidget()
        self.list_view.setMinimumWidth(500)
        self.list_view.setMinimumHeight(300)
        self.list_view.setItemDelegate(CustomListItemDelegate(self.list_view))
        self.message_box_layout.addWidget(self.list_view)
        self.list_view.itemClicked.connect(self.on_list_item_clicked)
        self.yesButton.setEnabled(False)

    def on_list_item_clicked(self):
        self.yesButton.setEnabled(True)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window() and e.type() == QEvent.Resize:
            self._adjustText()
        return super().eventFilter(obj, e)

class _MalDetailsThread(QThread):
    """Fetch MAL anime details off the GUI thread."""
    loaded = pyqtSignal(dict, str)  # (data, error_message)

    def __init__(self, anime_id, parent=None):
        super().__init__(parent)
        self.anime_id = anime_id

    def run(self):
        try:
            from ..common.mal import get_anime_details
            data = get_anime_details(self.anime_id)
            self.loaded.emit(data or {}, "")
        except Exception as e:
            self.loaded.emit({}, str(e))


class SyncDialog(MaskDialogBase, Ui_MessageBox):
    _SYN_MAX_CHARS = 360

    def __init__(self, anime, parent=None):
        super().__init__(parent)
        self._setUpUi(f"Anime Info — {anime.name}", "", self.widget)
        self.yesButton.setText("Update")
        # Hide the empty content label and shrink its slot so the body sits
        # right under the title.
        if hasattr(self, 'contentLabel') and self.contentLabel is not None:
            self.contentLabel.hide()

        self.anime = anime
        # Primary key is now the MAL ID (Anime.id was migrated from idMal).
        self.anime_id = anime.id
        self.img_size = (180, 260)
        self._details_thread = None

        # Theme palette
        if isDarkTheme():
            self._fg = "#e6e6e6"
            self._fg_dim = "#a8a8a8"
        else:
            self._fg = "#1a1a1a"
            self._fg_dim = "#606060"

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

        # Poster
        self.cover_image_label = QLabel()
        self.cover_image_label.setFixedSize(*self.img_size)
        self.load_img(anime.img, self.cover_image_label)
        self.message_box_layout.addWidget(self.cover_image_label, 0, Qt.AlignTop)

        # Right column
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        self.message_box_layout.addLayout(right_col, 1)

        # Title row: title (stretch) + Open-on-MAL icon (top-right, theme color)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_label = QLabel(anime.name)
        self.title_label.setStyleSheet(
            f"color: {self._fg}; font-size: 16px; font-weight: 600;"
        )
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, 1)

        mal_url = f"https://myanimelist.net/anime/{self.anime_id}"
        self.open_mal_btn = PrimaryToolButton(FluentIcon.LINK)
        self.open_mal_btn.setToolTip("Open on MyAnimeList")
        self.open_mal_btn.setFixedSize(30, 30)
        self.open_mal_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(mal_url))
        )
        title_row.addWidget(self.open_mal_btn, 0, Qt.AlignTop)
        right_col.addLayout(title_row)

        self.meta_label = QLabel("Loading details…")
        self.meta_label.setStyleSheet(
            f"color: {self._fg_dim}; font-size: 12px;"
        )
        self.meta_label.setWordWrap(True)
        right_col.addWidget(self.meta_label)

        self.aired_label = QLabel("")
        self.studios_label = QLabel("")
        self.genres_label = QLabel("")
        for lbl in (self.aired_label, self.studios_label, self.genres_label):
            lbl.setStyleSheet(f"color: {self._fg}; font-size: 12px;")
            lbl.setWordWrap(True)
            right_col.addWidget(lbl)

        # Synopsis (non-scrolling, truncates with … on overflow)
        right_col.addSpacing(4)
        self.synopsis = QLabel("Loading synopsis…")
        self.synopsis.setStyleSheet(
            f"color: {self._fg}; font-size: 12px;"
        )
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

        # Compact one-line form
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
            ['watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch']
        )
        self.status_combobox.setCurrentText('completed')
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

        # Async fetch
        self._details_thread = _MalDetailsThread(self.anime_id, self)
        self._details_thread.loaded.connect(self._on_details_loaded)
        self._details_thread.start()

    @staticmethod
    def _clean_synopsis(s):
        if not s:
            return ""
        s = s.strip()
        # Strip trailing source/credit blocks (any number, any order)
        pattern = re.compile(
            r'\s*(?:\[[^\]]*\]|\([^)]*?(?:Source|Written by)[^)]*\))\s*$',
            re.IGNORECASE,
        )
        prev = None
        while prev != s:
            prev = s
            s = pattern.sub('', s).rstrip()
        return s.strip()

    @classmethod
    def _truncate(cls, s, n=None):
        n = n or cls._SYN_MAX_CHARS
        if len(s) <= n:
            return s
        cut = s.rfind(' ', 0, n)
        if cut == -1:
            cut = n
        return s[:cut].rstrip(' ,.;:!?-—') + '…'

    def _on_details_loaded(self, data, err):
        if err or not data:
            self.synopsis.setText(
                "Could not load details from MyAnimeList."
                + (f"\n({err})" if err else "")
            )
            self.meta_label.setText("—")
            return

        title = data.get('title')
        if title:
            self.title_label.setText(title)

        bits = []
        if data.get('mean') is not None:
            bits.append(f"⭐ {data['mean']}")
        if data.get('rank'):
            bits.append(f"#{data['rank']}")
        if data.get('popularity'):
            bits.append(f"Pop #{data['popularity']}")
        if data.get('media_type'):
            bits.append(str(data['media_type']).upper())
        if data.get('num_episodes'):
            bits.append(f"{data['num_episodes']} ep")
        if data.get('status'):
            bits.append(str(data['status']).replace('_', ' ').title())
        self.meta_label.setText(" · ".join(bits) if bits else "")

        start = data.get('start_date', '')
        end = data.get('end_date', '')
        if start or end:
            self.aired_label.setText(f"Aired: {start or '?'} → {end or 'ongoing'}")

        studios = data.get('studios') or []
        if studios:
            self.studios_label.setText(
                "Studios: " + ", ".join(s.get('name', '') for s in studios)
            )

        genres = data.get('genres') or []
        if genres:
            self.genres_label.setText(
                "Genres: " + ", ".join(g.get('name', '') for g in genres)
            )

        synopsis = self._clean_synopsis(data.get('synopsis') or "")
        if not synopsis:
            synopsis = "(no synopsis available)"
        self.synopsis.setText(self._truncate(synopsis))

        # Pre-fill form from existing MAL list entry
        mls = data.get('my_list_status') or {}
        if mls.get('status'):
            idx = self.status_combobox.findText(mls['status'])
            if idx >= 0:
                self.status_combobox.setCurrentIndex(idx)
        if mls.get('score') is not None:
            self.score_spinbox.setValue(int(mls['score']))
        if mls.get('num_episodes_watched') is not None:
            self.watched_episodes.setValue(int(mls['num_episodes_watched']))

    def closeEvent(self, event):
        if self._details_thread and self._details_thread.isRunning():
            self._details_thread.quit()
            self._details_thread.wait(2000)
        super().closeEvent(event)

    def load_img(self, url, label):
        pixmap = get_img(url)
        scaled_pixmap = pixmap.scaled(
            self.img_size[0], self.img_size[1],
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window() and e.type() == QEvent.Resize:
            self._adjustText()
        return super().eventFilter(obj, e)

    def get_form_data(self):
        return {
            'anime_id': self.anime_id,
            'status': self.status_combobox.currentText(),
            'score': self.score_spinbox.value(),
            'num_watched_episodes': self.watched_episodes.value()
        }

class AnimeDialog(MaskDialogBase, Ui_MessageBox):
    def __init__(self, anime, parent=None):
        super().__init__(parent)
        title = "Verify and Confirm Info"
        content = "Make sure this info is correct and make corrections as necessary and Make sure of season no.\nPLEASE REMOVE SEASON AND PART FROM THE TITLE \neg. 'Attack on Titan Season 2' should be 'Attack on Titan' \nor  'Nanatsu no Taizai: Kamigami no Gekirin' should be 'Nanatsu no Taizai'"
        self._setUpUi(title, content, self.widget)
        self.yesButton.setText("Confirm")

        # Create a layout for the message box
        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)
        self.message_box_layout = QHBoxLayout()
        self.message_box_layout.setContentsMargins(24, 0, 24, 0)
        self.textLayout.setContentsMargins(24, 24, 24, 0)
        self.vBoxLayout.insertLayout(1, self.message_box_layout)

        img = anime['coverImage']['extraLarge']
        name = anime['title']['romaji']
        airing = anime['status'] in ['RELEASING', 'HIATUS', 'CANCELLED']
        season = anime['season']
        total_ep = anime['episodes'] if anime['episodes'] else 13
        airing_ep = anime['nextAiringEpisode']['episode'] if airing and anime['nextAiringEpisode'] else total_ep

        # Show the cover image on the left side of the dialog
        cover_image_label = QLabel()
        self.message_box_layout.addWidget(cover_image_label, Qt.AlignLeft)
        self.img_size = (164, 240)
        self.load_img(img, cover_image_label)

        # Create a form layout for the anime info on the right side of the dialog
        form_layout = QFormLayout()
        self.message_box_layout.addLayout(form_layout, Qt.AlignRight)

        # Add the anime title
        self.title_label = LineEdit(self)
        self.title_label.setText(name)
        self.title_label.setMinimumWidth(300)
        form_layout.addRow('Title:', self.title_label)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(8)        # Add a spin box for the season
        self.season = SpinBox(self)
        self.season.setRange(1, 9999)  # Allow seasons up to 9999
        self.season.setValue(season)
        form_layout.addRow('Season:', self.season)        # Add a spin box for the next airing episode (only enabled if status is RELEASING)
        if airing:
            self.next_airing_episode = SpinBox(self)
            self.next_airing_episode.setRange(1, 9999)  # Allow episodes up to 9999
            self.next_airing_episode.setEnabled(airing)
            self.next_airing_episode.setValue(airing_ep)
            form_layout.addRow('Next Airing Episode:', self.next_airing_episode)        # Add a spin box for the number of episodes
        self.episodes = SpinBox(self)
        self.episodes.setRange(1, 9999)  # Allow episodes up to 9999
        self.episodes.setValue(total_ep)
        form_layout.addRow('Total Episodes:', self.episodes)        # Add a combo box for the status
        self.status_combobox = ComboBox(self)
        self.status_combobox.addItems(['FINISHED', 'RELEASING', 'NOT_YET_RELEASED', 'CANCELLED', 'HIATUS'])
        self.status_combobox.setCurrentText(anime['status'])
        self.status_combobox.setEnabled(False)
        form_layout.addRow('Status:', self.status_combobox)

        self.download_type = ComboBox(self)
        self.download_type.addItems(['Full', 'Episodewise'])
        self.download_type.setCurrentText('Episodewise' if airing else 'Full')
        form_layout.addRow('Download Type:', self.download_type)

        self.from_download = SpinBox(self)
        self.from_download.setRange(1, 9999)  # Allow episodes up to 9999
        self.from_download.setValue(1)

        self.to_download = SpinBox(self)
        self.to_download.setRange(1, 9999)  # Allow episodes up to 9999
        self.to_download.setValue(total_ep)

        self.from_download_label = QLabel('Download from episode:')
        self.to_download_label = QLabel('Download to episode:')

        form_layout.addRow(self.from_download_label, self.from_download)
        form_layout.addRow(self.to_download_label, self.to_download)

        self.update_widgets()
        self.download_type.currentTextChanged.connect(self.update_widgets)

    def load_img(self, url, label):
        pixmap = get_img(url)
        scaled_pixmap = pixmap.scaled(self.img_size[0], self.img_size[1])
        label.setPixmap(scaled_pixmap)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window() and e.type() == QEvent.Resize:
            self._adjustText()
        return super().eventFilter(obj, e)

    def update_widgets(self):
        if self.download_type.currentText() == "Full":
            self.from_download.hide()
            self.to_download.hide()
            self.from_download_label.hide()
            self.to_download_label.hide()
        else:
            self.from_download.show()
            self.to_download.show()
            self.from_download_label.show()
            self.to_download_label.show()
