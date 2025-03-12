# download_interface.py (updated)
from PyQt5.QtWidgets import QLabel, QListWidget, QListWidgetItem, QProgressBar
from PyQt5.QtCore import Qt
from .base_interface import BaseInterface
from ..common.style_sheet import StyleSheet

class DownloadInterface(BaseInterface):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.download_list = QListWidget(self)
        self.vBoxLayout.addWidget(self.download_list)
        StyleSheet.DOWNLOAD_INTERFACE.apply(self)
    def load_active_downloads(self, animes):
        """Load active downloads from saved state."""
        for anime in animes:
            for name, _, _ in anime.active_downloads:
                self.add_download(name) 
    def add_download(self, name):
        """Add a new download entry to the UI."""
        item = QListWidgetItem()
        widget = QProgressBar()
        widget.setFormat(f'{name} - 0.0%')
        widget.setValue(0)
        self.download_list.addItem(item)
        self.download_list.setItemWidget(item, widget)
        return widget

    def update_progress(self, name, progress, speed):
        """Update the progress bar for a download."""
        for i in range(self.download_list.count()):
            item = self.download_list.item(i)
            widget = self.download_list.itemWidget(item)
            if name in widget.format():
                widget.setValue(int(progress))
                widget.setFormat(f'{name} - {progress:.1f}% ({speed/1024:.1f} KB/s)')