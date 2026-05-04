# coding: utf-8
"""Reusable Fluent list-picker dialog."""
from PyQt5.QtCore import QEvent, QModelIndex, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QStyleOptionViewItem, QVBoxLayout
from qfluentwidgets import ListItemDelegate, ListWidget
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox

from ..config.config import cfg


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
