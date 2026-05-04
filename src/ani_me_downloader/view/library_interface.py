# coding: utf-8
"""Library grid: anime cards with progress overlay + sync/delete/watch buttons."""
from PyQt5.QtCore import QRect, QRectF, QSize, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QPainter, QPainterPath
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import Action, FlowLayout, FluentIcon, PrimaryToolButton, PushButton, RoundMenu

from ..core.anime import Anime, EpStatus
from ..core.time_util import get_time_difference
from ..config.config import cfg
from ..metadata.mal import update_anime_status
from .base_interface import BaseInterface
from .image_cache import get_img
from .style_sheet import StyleSheet
from qfluentwidgets import ScrollArea


_DOWNLOADED = {EpStatus.DONE, EpStatus.BATCH_DONE}


def _downloaded_count(anime: Anime) -> tuple[int, bool]:
    """Returns (count, fully_downloaded). Batch counts as total_episodes."""
    has_batch_done = any(ep.status is EpStatus.BATCH_DONE and ep.ep == 0 for ep in anime.episodes)
    if has_batch_done:
        return anime.total_episodes, True
    count = sum(1 for ep in anime.episodes if ep.status is EpStatus.DONE)
    return count, count >= anime.total_episodes > 0


class ImageLabel(QLabel):
    delete_signal = pyqtSignal(int)
    anime_sync_signal = pyqtSignal(int)

    def __init__(self, anime: Anime, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anime = anime
        self.setMouseTracking(True)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRect(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 20, 20)
        painter.setClipPath(path)
        if self.pixmap():
            painter.drawPixmap(rect, self.pixmap())

        bottom_h = int(self.height() * 0.07)
        bottom_rect = QRect(0, self.height() - bottom_h, self.width(), bottom_h + 1)
        painter.fillRect(bottom_rect, QColor("black"))

        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.setPen(QColor("white"))

        if self.anime.is_airing:
            airing_text = f"A{self.anime.last_aired_episode}"
            airing_rect = QRect(10, self.height() - bottom_h, 25, bottom_h)
            painter.fillRect(QRect(0, self.height() - bottom_h, 35, bottom_h), QColor("green"))
            painter.drawText(airing_rect, Qt.AlignCenter, airing_text)

        ep_dn, _ = _downloaded_count(self.anime)
        dn_rect = QRect(self.width() - 58, self.height() - bottom_h, 25, bottom_h)
        painter.fillRect(dn_rect, QColor("blue"))
        painter.drawText(dn_rect, Qt.AlignCenter, f"D{ep_dn}")

        total_rect = QRect(self.width() - 33, self.height() - bottom_h, 25, bottom_h)
        painter.fillRect(QRect(self.width() - 33, self.height() - bottom_h, 33, bottom_h), QColor("grey"))
        painter.drawText(total_rect, Qt.AlignCenter, f"T{self.anime.total_episodes}")

    def enterEvent(self, event):
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)

        sync_button = PrimaryToolButton(FluentIcon.INFO)
        sync_button.setFixedSize(38, 38)
        sync_button.setIconSize(QSize(20, 20))
        sync_button.clicked.connect(self.on_sync_button_clicked)
        button_layout.addWidget(sync_button)
        button_layout.addStretch()

        delete_button = PrimaryToolButton(FluentIcon.DELETE)
        delete_button.setFixedSize(38, 38)
        delete_button.setIconSize(QSize(20, 20))
        delete_button.clicked.connect(self.on_delete_button_clicked)
        button_layout.addWidget(delete_button)
        self.layout.addLayout(button_layout, 0)

        ep_dn, fully = _downloaded_count(self.anime)
        labels: list[QLabel] = []

        if self.anime.is_airing:
            d, h, m = get_time_difference(self.anime.next_eta)
            labels.append(QLabel(f"Next Airing: {self.anime.last_aired_episode + 1}"))
            labels.append(QLabel(f"Time Left: {d} days {h} hrs" if d else f"Time Left: {h} hrs {m} mins"))
            labels.append(QLabel(f"Downloaded: {ep_dn}"))
            labels.append(QLabel(f"Episodes: {self.anime.total_episodes}"))
        else:
            labels.append(QLabel(f"Downloaded: {ep_dn}"))
            labels.append(QLabel(f"Episodes: {self.anime.total_episodes}"))
            if fully:
                labels.append(QLabel("Completely Downloaded"))
            else:
                labels.append(QLabel(f"{ep_dn} out of {self.anime.total_episodes} episodes done"))

        for label in labels:
            label.setMinimumHeight(30)
            label.setMaximumHeight(30)
            label.setObjectName("animeInfo")
            self.layout.addWidget(label, alignment=Qt.AlignTop)

        c = cfg.themeColor.value
        self.setStyleSheet(f"background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 210);")

    def leaveEvent(self, event):
        self.setStyleSheet("background-color: transparent;")
        for label in self.findChildren(QLabel):
            label.deleteLater()
        for button in self.findChildren(PrimaryToolButton):
            button.deleteLater()
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if isinstance(item, QHBoxLayout):
                while item.count():
                    w = item.takeAt(0)
                    if w.widget():
                        w.widget().deleteLater()
                self.layout.removeItem(item)

    def on_delete_button_clicked(self):
        self.delete_signal.emit(self.anime.id)

    def on_sync_button_clicked(self):
        self.anime_sync_signal.emit(self.anime.id)


class LibraryInterface(BaseInterface):
    """Anime grid view."""
    deleteSignal = pyqtSignal(int)

    def __init__(self, animes: list[Anime], parent=None):
        super().__init__(parent=parent)
        scroll = ScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vBoxLayout.addWidget(scroll)
        grid_widget = QFrame()
        self.grid_layout = FlowLayout(self, needAni=True)
        self.grid_layout._verticalSpacing = 0
        self.grid_layout._horizontalSpacing = 0
        grid_widget.setLayout(self.grid_layout)
        scroll.setWidget(grid_widget)
        scroll.setWidgetResizable(True)

        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(2, 2, 0, 0)

        StyleSheet.LIBRARY_INTERFACE.apply(self)
        self._parent = parent
        self.animes = animes
        self.empty_label_visible = False
        self.title_label: QLabel | None = None

        if not self.animes:
            self.empty_label_visible = True
            self.title_label = QLabel("Add Anime from Search to see here")
            self.title_label.setObjectName("title")
            self.vBoxLayout.addWidget(self.title_label, Qt.AlignCenter)

        self.img_size = (164, 240)
        self.update_grid(self.animes)

    def update_grid(self, animes: list[Anime]) -> None:
        self.animes = animes
        if self.empty_label_visible and self.animes and self.title_label:
            self.title_label.setParent(None)
            self.title_label.deleteLater()
            self.title_label = None
            self.empty_label_visible = False

        while self.grid_layout.count():
            w = self.grid_layout.takeAt(0)
            if w:
                w.setParent(None)
                w.deleteLater()

        for anime in self.animes:
            cell = QWidget()
            cell_layout = QVBoxLayout()
            cell.setLayout(cell_layout)
            cell.setObjectName("animeBox")
            self.grid_layout.addWidget(cell)

            image_label = ImageLabel(anime)
            image_label.setFixedSize(*self.img_size)
            image_label.setStyleSheet("background-color: transparent;")
            image_label.delete_signal.connect(self.on_delete_signal)
            image_label.anime_sync_signal.connect(self.on_sync_button_clicked)
            cell_layout.addWidget(image_label, alignment=Qt.AlignCenter)
            self._load_img(anime.img, image_label)

            name = anime.name if len(anime.name) <= 44 else anime.name[:44] + "..."
            title_label = QLabel(name)
            title_label.setObjectName("animeTitle")
            title_label.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(title_label)

            button_layout = QHBoxLayout()
            cell_layout.addLayout(button_layout)

            watch_online = PushButton("Watch Online")
            watch_online.setObjectName("button")
            urls = anime.watch_urls or {}
            if not urls:
                watch_online.setEnabled(False)
            elif len(urls) == 1:
                only_url = next(iter(urls.values()))
                watch_online.clicked.connect(self._open_url(only_url))
            else:
                watch_online.clicked.connect(self._make_provider_menu(watch_online, urls))
            button_layout.addWidget(watch_online)

            watch_local = PushButton("Watch Local")
            watch_local.setObjectName("button")
            watch_local.clicked.connect(self._open_path(anime.output_dir))
            button_layout.addWidget(watch_local)

    def _load_img(self, url: str, label: QLabel) -> None:
        pixmap = get_img(url)
        scaled = pixmap.scaled(*self.img_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    @staticmethod
    def _open_url(url: str):
        return lambda: QDesktopServices.openUrl(QUrl(url))

    def _make_provider_menu(self, anchor, urls: dict[str, str]):
        def show():
            menu = RoundMenu(parent=anchor)
            for name in sorted(urls):
                action = Action(FluentIcon.LINK, name.capitalize(), self)
                url = urls[name]
                action.triggered.connect(lambda _checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
                menu.addAction(action)
            menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        return show

    @staticmethod
    def _open_path(path: str):
        return lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def on_sync_button_clicked(self, anime_id: int) -> None:
        from ..components.sync_dialog import SyncDialog
        anime = next((a for a in self.animes if a.id == anime_id), None)
        if anime is None:
            return
        coordinator = getattr(self._parent, "coordinator", None)
        dialog = SyncDialog(anime, self, coordinator=coordinator)
        if dialog.exec_():
            try:
                update_anime_status(**dialog.get_form_data())
                if self._parent and hasattr(self._parent, "notifications"):
                    self._parent.notifications.success("Anime status updated successfully")
            except Exception as e:
                print(f"Error updating anime status: {e}")

    def on_delete_signal(self, anime_id: int) -> None:
        from qfluentwidgets import MessageBox
        anime = next((a for a in self.animes if a.id == anime_id), None)
        if anime is None:
            return
        msg = MessageBox(
            "Confirm Delete",
            f"Are you sure you want to delete {anime.name} from your library? "
            "This will also delete all downloaded files.",
            parent=self,
        )
        if msg.exec_():
            self.deleteSignal.emit(anime_id)
