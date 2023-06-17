# coding:utf-8
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

from .base_interface import BaseInterface

class DownloadInterface(BaseInterface):
    """ Download interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.label = QLabel("Coming Soon", self)
        font = self.label.font()
        font.setPointSize(24) # Set font size
        font.setBold(True) # Set font to bold
        font.setItalic(True) # Set font to italic
        self.label.setFont(font)
        self.label.setStyleSheet("color: #ffffff")
        self.label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)