# coding: utf-8
"""Toast notification helpers used by MainWindow."""
from PyQt5.QtCore import QObject
from qfluentwidgets import InfoBar, InfoBarIcon, StateToolTip

from ..config.config import cfg


class Notifications(QObject):
    """Wraps InfoBar plus the special-cased 'searching' state tooltip."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_widget = parent
        self._searching_box: StateToolTip | None = None

    def info(self, text: str) -> None:
        if "searching" in text:
            self._searching_box = StateToolTip("Searching", "searching for torrents", self.parent_widget)
            p = self.parent_widget
            self._searching_box.move(
                int(p.width() - (self._searching_box.width() + 10)),
                int(p.height() - (self._searching_box.height() + 10)),
            )
            self._searching_box.show()
            return
        if cfg.showNotification.value:
            InfoBar(
                icon=InfoBarIcon.INFORMATION,
                title="Info",
                content=text,
                duration=6000,
                parent=self.parent_widget,
            ).show()

    def error(self, text: str) -> None:
        if "searching" in text:
            if self._searching_box is not None:
                self._searching_box.setState(True)
                self._searching_box = None
            return
        InfoBar(
            icon=InfoBarIcon.ERROR,
            title="Error",
            content=text,
            duration=6000,
            parent=self.parent_widget,
        ).show()

    def success(self, text: str) -> None:
        if cfg.showNotification.value:
            InfoBar(
                icon=InfoBarIcon.SUCCESS,
                title="Success",
                content=text,
                duration=6000,
                parent=self.parent_widget,
            ).show()
