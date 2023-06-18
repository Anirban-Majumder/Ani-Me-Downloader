# coding:utf-8
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

from .base_interface import BaseInterface
from ..common.style_sheet import StyleSheet

class DownloadInterface(BaseInterface):
    """ Download interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.label = QLabel("Coming Soon", self)
        self.label.setObjectName("title")
        self.vBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        StyleSheet.DOWNLOAD_INTERFACE.apply(self)
