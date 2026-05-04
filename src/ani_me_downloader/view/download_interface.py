# coding: utf-8
"""Active downloads tree + per-torrent file panel. Keyed by info_hash."""
import math
import os

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.torrent import FilePriority, Torrent
from .style_sheet import StyleSheet
from .base_interface import BaseInterface


_PRIORITY_LABEL = {
    FilePriority.SKIP: "Skip",
    FilePriority.LOW: "Low",
    FilePriority.NORMAL: "Normal",
    FilePriority.HIGH: "High",
}
_LABEL_PRIORITY = {v: k for k, v in _PRIORITY_LABEL.items()}


def _format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    return f"{round(size_bytes / math.pow(1024, i), 2)} {units[i]}"


def _format_speed(bytes_per_sec: int) -> str:
    if bytes_per_sec <= 0:
        return "0"
    return f"{bytes_per_sec / 1024:.1f}"


def _format_eta(seconds: int) -> str:
    if seconds <= 0:
        return "∞"
    if seconds < 60:
        return f"{int(seconds)} sec"
    if seconds < 3600:
        return f"{int(seconds / 60)} min"
    h = int(seconds / 3600)
    m = int((seconds % 3600) / 60)
    return f"{h} hr {m} min"


class DownloadInterface(BaseInterface):
    """Tree of active torrents. Emits info_hash on user actions."""
    pauseResumeSignal = pyqtSignal(str)
    deleteSignal = pyqtSignal(str, bool)
    changePrioritySignal = pyqtSignal(str, int, object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("downloadInterface")

        self.splitter = QSplitter(Qt.Vertical, self)
        self.torrent_list = QTreeWidget()
        self.torrent_list.setIndentation(0)
        self.torrent_list.setObjectName("torrentList")
        self.torrent_list.setUniformRowHeights(True)
        self.torrent_list.setColumnCount(9)
        self.torrent_list.setHeaderLabels(
            ["Name", "Size", "Progress", "Status", "Seeds", "Peers", "DL Speed", "UL Speed", "ETA"]
        )
        self.torrent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.torrent_list.customContextMenuRequested.connect(self._show_context_menu)
        self.torrent_list.itemClicked.connect(self._on_item_clicked)
        self.torrent_list.setAlternatingRowColors(True)
        self.torrent_list.setSortingEnabled(True)
        self.splitter.addWidget(self.torrent_list)

        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("detailPanel")
        self.detail_panel.setMinimumHeight(200)
        self.panel_visible = True

        detail_layout = QVBoxLayout(self.detail_panel)
        button_layout = QHBoxLayout()

        self.detail_button = QPushButton("Details")
        self.content_button = QPushButton("Content")
        self.detail_button.clicked.connect(lambda: self.show_panel("detail"))
        self.content_button.clicked.connect(lambda: self.show_panel("content"))
        self.toggle_panel_button = QPushButton("Hide Details")
        self.toggle_panel_button.clicked.connect(self.toggle_panel)
        button_layout.addStretch()
        button_layout.addWidget(self.toggle_panel_button)
        button_layout.addWidget(self.detail_button)
        button_layout.addWidget(self.content_button)
        detail_layout.addLayout(button_layout)

        self.panel_stack = QStackedWidget()

        self.detail_page = QWidget()
        dp_layout = QVBoxLayout(self.detail_page)
        self.detail_label = QLabel("Select a torrent to see details.")
        self.detail_label.setWordWrap(True)
        self.detail_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        dp_layout.addWidget(self.detail_label)

        self.content_page = QWidget()
        cp_layout = QVBoxLayout(self.content_page)
        self.content_tree = QTreeWidget()
        self.content_tree.setIndentation(0)
        self.content_tree.setObjectName("contentTree")
        self.content_tree.setAlternatingRowColors(True)
        self.content_tree.setColumnCount(5)
        self.content_tree.setHeaderLabels(["Name", "Size", "Progress", "Priority", "Remaining"])
        cp_layout.addWidget(self.content_tree)

        self.panel_stack.addWidget(self.detail_page)
        self.panel_stack.addWidget(self.content_page)
        detail_layout.addWidget(self.panel_stack)
        self.detail_panel.setMaximumHeight(0)
        self.splitter.addWidget(self.detail_panel)

        self.vBoxLayout.addWidget(self.splitter)
        StyleSheet.DOWNLOAD_INTERFACE.apply(self)

        self.torrent_items: dict[str, QTreeWidgetItem] = {}
        self.torrent_data: dict[str, Torrent] = {}
        self.current_ih: str | None = None
        self._resize_columns()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_columns()

    def _resize_columns(self):
        w = self.torrent_list.width()
        for i, frac in enumerate((0.35, 0.10, 0.15, 0.12, 0.07, 0.07, 0.11, 0.11, 0.07)):
            self.torrent_list.setColumnWidth(i, int(w * frac))
        cw = self.content_tree.width()
        for i, frac in enumerate((0.40, 0.10, 0.20, 0.15, 0.15)):
            self.content_tree.setColumnWidth(i, int(cw * frac))

    def toggle_panel(self):
        if self.panel_visible:
            sizes = self.splitter.sizes()
            self.splitter.setSizes([sizes[0] + sizes[1], 0])
            self.toggle_panel_button.setText("Show Details")
            self.panel_visible = False
        else:
            total = self.splitter.height()
            self.splitter.setSizes([int(total * 0.7), int(total * 0.3)])
            self.toggle_panel_button.setText("Hide Details")
            self.panel_visible = True

    def show_panel(self, panel_type: str) -> None:
        if not self.panel_visible:
            self.toggle_panel()
        self.detail_panel.setMaximumHeight(int(2 * self.height() / 3))
        if panel_type == "detail":
            self.panel_stack.setCurrentWidget(self.detail_page)
            self.detail_button.setStyleSheet("background-color: #29f1ff;")
            self.content_button.setStyleSheet("")
        else:
            self.panel_stack.setCurrentWidget(self.content_page)
            self.content_button.setStyleSheet("background-color: #29f1ff;")
            self.detail_button.setStyleSheet("")

    def set_torrent_data(self, torrents: list[Torrent]) -> None:
        """Initial population. Replaces all rows tracked by info_hash."""
        self.torrent_data = {t.info_hash: t for t in torrents}
        for t in torrents:
            if t.info_hash not in self.torrent_items:
                self._add_row(t.info_hash, t.name)
            snapshot = {
                "name": t.name,
                "status": t.desired_state.value,
                "progress": t.progress,
                "size_bytes": t.size_bytes,
                "dl_speed": t.dl_speed,
                "ul_speed": t.ul_speed,
                "eta": t.eta,
                "seeds": t.seeds,
                "peers": t.peers,
            }
            self.update_progress(t.info_hash, snapshot)

    def add_torrent(self, t: Torrent) -> None:
        self.torrent_data[t.info_hash] = t
        if t.info_hash not in self.torrent_items:
            self._add_row(t.info_hash, t.name)

    def _add_row(self, info_hash: str, name: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name, "", "", "pending", "", "", "0", "0", "0"])
        item.setData(0, Qt.UserRole, info_hash)
        self.torrent_list.addTopLevelItem(item)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        self.torrent_list.setItemWidget(item, 2, bar)
        self.torrent_items[info_hash] = item
        return item

    def update_progress(self, info_hash: str, snap: dict) -> None:
        item = self.torrent_items.get(info_hash)
        if item is None:
            t = self.torrent_data.get(info_hash)
            name = t.name if t else snap.get("name", info_hash[:8])
            item = self._add_row(info_hash, name)

        bar = self.torrent_list.itemWidget(item, 2)
        progress = float(snap.get("progress", 0.0))
        if bar:
            bar.setValue(int(progress))
            bar.setFormat(f"{progress:.1f}%")
        item.setText(1, _format_size(int(snap.get("size_bytes", 0))))
        item.setText(3, str(snap.get("status", "")))
        item.setText(4, str(snap.get("seeds", 0)))
        item.setText(5, str(snap.get("peers", 0)))
        item.setText(6, _format_speed(int(snap.get("dl_speed", 0))))
        item.setText(7, _format_speed(int(snap.get("ul_speed", 0))))
        item.setText(8, _format_eta(int(snap.get("eta", 0))))

        if self.current_ih == info_hash:
            self._populate_detail_panel(item)

    def remove_torrent(self, info_hash: str) -> None:
        item = self.torrent_items.pop(info_hash, None)
        if item is not None:
            idx = self.torrent_list.indexOfTopLevelItem(item)
            if idx >= 0:
                self.torrent_list.takeTopLevelItem(idx)
        self.torrent_data.pop(info_hash, None)
        if self.current_ih == info_hash:
            self.current_ih = None
            self.detail_label.setText("Select a torrent to see details.")
            self.content_tree.clear()

    def _on_item_clicked(self, item, _column):
        ih = item.data(0, Qt.UserRole)
        if not isinstance(ih, str):
            return
        self.current_ih = ih
        self._populate_detail_panel(item)
        if not self.panel_visible:
            self.toggle_panel()
        self.show_panel("detail")

    def _populate_detail_panel(self, item: QTreeWidgetItem) -> None:
        ih = item.data(0, Qt.UserRole)
        if not isinstance(ih, str):
            return
        self.current_ih = ih
        self.detail_label.setText(
            f"Name: {item.text(0)}\nSize: {item.text(1)}\nStatus: {item.text(3)}\n"
            f"Seeds: {item.text(4)}\nPeers: {item.text(5)}\nDL Speed: {item.text(6)} KB/s\n"
            f"UL Speed: {item.text(7)} KB/s\nETA: {item.text(8)}"
        )
        self.content_tree.clear()
        t = self.torrent_data.get(ih)
        if t is None or not t.files:
            self.content_tree.addTopLevelItem(
                QTreeWidgetItem(["No files available or metadata not yet received"])
            )
            return
        for index, f in enumerate(t.files):
            row = QTreeWidgetItem(
                [
                    os.path.basename(f.path),
                    _format_size(f.size_bytes),
                    "",
                    _PRIORITY_LABEL[f.priority],
                    _format_size(f.remaining_bytes),
                ]
            )
            self.content_tree.addTopLevelItem(row)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(f.progress))
            bar.setTextVisible(True)
            bar.setFormat(f"{f.progress:.1f}%")
            self.content_tree.setItemWidget(row, 2, bar)

            combo = QComboBox()
            combo.addItems(["Skip", "Low", "Normal", "High"])
            combo.setCurrentText(_PRIORITY_LABEL[f.priority])
            combo.currentTextChanged.connect(
                lambda value, idx=index, h=ih: self.changePrioritySignal.emit(
                    h, idx, _LABEL_PRIORITY[value]
                )
            )
            self.content_tree.setItemWidget(row, 3, combo)

    def _show_context_menu(self, pos):
        item = self.torrent_list.itemAt(pos)
        if item is None:
            return
        ih = item.data(0, Qt.UserRole)
        menu = QMenu()
        status = item.text(3).lower()

        a_pause = QAction("Resume" if status == "paused" else "Pause", self)
        a_open = QAction("Open Containing Folder", self)
        a_del = QAction("Delete", self)
        a_del_files = QAction("Delete with Files", self)

        menu.addAction(a_pause)
        menu.addAction(a_open)
        menu.addSeparator()
        menu.addAction(a_del)
        menu.addAction(a_del_files)

        a_pause.triggered.connect(lambda: self.pauseResumeSignal.emit(ih))
        a_open.triggered.connect(lambda: self._open_torrent_folder(ih))
        a_del.triggered.connect(lambda: self.deleteSignal.emit(ih, False))
        a_del_files.triggered.connect(lambda: self.deleteSignal.emit(ih, True))

        menu.exec_(self.torrent_list.viewport().mapToGlobal(pos))
        self._populate_detail_panel(item)

    def _open_torrent_folder(self, info_hash: str) -> None:
        t = self.torrent_data.get(info_hash)
        if t and t.save_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(t.save_path))
