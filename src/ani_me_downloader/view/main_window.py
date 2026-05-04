# coding: utf-8
"""FluentWindow shell. Owns interfaces, wires Coordinator signals."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QHBoxLayout,
    QListWidgetItem,
    QMenu,
    QSystemTrayIcon,
)
from qfluentwidgets import (
    FluentWindow,
    NavigationInterface,
    NavigationItemPosition,
)
from qfluentwidgets import FluentIcon as FIF

from ..config.config import cfg
from ..config.paths import get_r_path
from ..services.coordinator import Coordinator
from .style_sheet import StyleSheet
from .download_interface import DownloadInterface
from .library_interface import LibraryInterface
from .notifications import Notifications
from .search_interface import SearchInterface
from .setting_interface import SettingInterface
from .title_bar import CustomTitleBar


class MainWindow(FluentWindow):
    """Top-level window. View-only; all writes go through Coordinator."""

    def __init__(self, coordinator: Coordinator):
        super().__init__()
        self.coordinator = coordinator
        self._init_layout()

        self.notifications = Notifications(self)
        self.searchInterface = SearchInterface(self)
        self.libraryInterface = LibraryInterface(coordinator.state.animes, self)
        self.downloadInterface = DownloadInterface(self)
        self.downloadInterface.set_torrent_data(coordinator.state.torrents)
        self.settingInterface = SettingInterface(self)

        self._init_navigation()
        self._wire_signals()
        self._init_window()

    def _init_layout(self):
        self.setTitleBar(CustomTitleBar(self))
        self.hBoxLayout.removeWidget(self.navigationInterface)
        self.widgetLayout.removeWidget(self.navigationInterface)
        self.navigationInterface.setParent(None)
        self.navigationInterface = NavigationInterface(self, showReturnButton=False)
        self.widgetLayout = QHBoxLayout()

        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addLayout(self.widgetLayout)
        self.hBoxLayout.setStretchFactor(self.widgetLayout, 1)

        self.widgetLayout.addWidget(self.stackedWidget)
        self.widgetLayout.setContentsMargins(0, 48, 0, 0)

        self.navigationInterface.displayModeChanged.connect(self.titleBar.raise_)
        self.titleBar.raise_()

    def _init_navigation(self):
        self.searchInterface.setObjectName("searchInterface")
        self.libraryInterface.setObjectName("libraryInterface")
        self.downloadInterface.setObjectName("downloadInterface")
        self.settingInterface.setObjectName("settingInterface")

        self.addSubInterface(self.searchInterface, FIF.SEARCH, "Search")
        self.addSubInterface(self.libraryInterface, FIF.BOOK_SHELF, "Library")
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.downloadInterface, FIF.DOWNLOAD, "Download")
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, "Settings", NavigationItemPosition.BOTTOM
        )

    def _wire_signals(self):
        c = self.coordinator

        self.searchInterface.addSignal.connect(c.add_anime)
        self.libraryInterface.deleteSignal.connect(c.remove_anime)
        self.downloadInterface.pauseResumeSignal.connect(c.toggle_pause)
        self.downloadInterface.deleteSignal.connect(self._on_delete_torrent)
        self.downloadInterface.changePrioritySignal.connect(c.change_file_priority)

        c.info.connect(self.notifications.info)
        c.error.connect(self.notifications.error)
        c.success.connect(self.notifications.success)
        c.selection_needed.connect(self._show_selection_dialog)
        c.animes_changed.connect(self._refresh_library)
        c.torrents_changed.connect(self._refresh_downloads)
        c.torrent_progress.connect(self.downloadInterface.update_progress)
        c.torrent_files_updated.connect(self._on_torrent_files_updated)

    def _on_delete_torrent(self, info_hash: str, delete_files: bool):
        self.coordinator.delete_torrent(info_hash, delete_files=delete_files)

    def _refresh_library(self):
        self.libraryInterface.update_grid(self.coordinator.state.animes)

    def _refresh_downloads(self):
        current_hashes = {t.info_hash for t in self.coordinator.state.torrents}
        view_hashes = set(self.downloadInterface.torrent_items.keys())
        for ih in view_hashes - current_hashes:
            self.downloadInterface.remove_torrent(ih)
        for t in self.coordinator.state.torrents:
            if t.info_hash not in self.downloadInterface.torrent_items:
                self.downloadInterface.add_torrent(t)

    def _on_torrent_files_updated(self, info_hash: str):
        if self.downloadInterface.current_ih == info_hash:
            item = self.downloadInterface.torrent_items.get(info_hash)
            if item is not None:
                self.downloadInterface._populate_detail_panel(item)

    def _show_selection_dialog(self, anime_id: int, results: list):
        from ..components.list_dialog import ListDialog
        dialog = ListDialog(
            "Torrent Results, Please Choose:",
            "We could not auto-pick a torrent. Pick one from the list below:",
            self,
        )
        max_seeds = max((r.seeds for r in results), default=0)
        width = max(1, len(str(max_seeds)))
        for r in results:
            item = QListWidgetItem(f"{r.seeds:0{width}d} | {r.size} || {r.title}")
            item.setData(Qt.UserRole, r)
            dialog.list_view.addItem(item)
        if dialog.exec_():
            selected = dialog.list_view.currentItem().data(Qt.UserRole)
            self.coordinator.receive_torrent_choice(anime_id, selected)

    def _init_window(self):
        self.resize(850, 700)
        self.setMinimumWidth(600)
        self.logo = QIcon(get_r_path("logo.png"))
        self.setWindowIcon(self.logo)
        self.setWindowTitle("  Ani-Me  Downloader  ")
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        StyleSheet.MAIN_WINDOW.apply(self)

    def _create_tray_icon(self):
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.showNormal)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.quit)
        tray_menu = QMenu(self)
        tray_menu.addAction(show_action)
        tray_menu.addAction(exit_action)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.logo)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        self.coordinator.shutdown(timeout_seconds=5)
        super().closeEvent(event)

    def show_first_time(self):
        import os

        from qfluentwidgets import MessageBox

        from .constants import about_text, terms_text
        user = os.getlogin()
        msg = MessageBox(f"Welcome {user} to Ani-Me Downloader", terms_text, self)
        msg.yesButton.setText("I Agree")
        msg.cancelButton.setText("I Disagree")
        if msg.exec_():
            msg2 = MessageBox(
                f"Hello, {user} here's a quick tour of Ani-Me Downloader",
                about_text,
                self,
            )
            msg2.yesButton.setText("Okay")
            if msg2.exec_():
                cfg.set(cfg.firstTime, False)
