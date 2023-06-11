# coding:utf-8
from PyQt5.QtCore import Qt, QRect, QRectF, QEasingCurve
from PyQt5.QtCore import pyqtSignal, QModelIndex
from PyQt5.QtGui import  QPainter, QPen, QColor, QPainterPath
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
                             QWidget, QVBoxLayout, QLabel, QStyleOptionViewItem)

from qfluentwidgets import (ScrollArea, PopUpAniStackedWidget, FluentIcon,
                            PrimaryToolButton, ListItemDelegate, isDarkTheme)

from ..common.style_sheet import StyleSheet
from ..common.config import cfg

class SeparatorWidget(QWidget):
    """ Seperator widget """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(6, 16)

    def paintEvent(self, e):
        painter = QPainter(self)
        pen = QPen(1)
        pen.setCosmetic(True)
        c = QColor(255, 255, 255, 21) if isDarkTheme() else QColor(0, 0, 0, 15)
        pen.setColor(c)
        painter.setPen(pen)

        x = self.width() // 2
        painter.drawLine(x, 0, x, self.height())


class ImageLabel(QLabel):
    delete_signal = pyqtSignal(int)

    def __init__(self, anime, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anime = anime
        self.setMouseTracking(True)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

    def paintEvent(self, event):
        #TODO make the rect slyanted
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the image with rounded corners
        rect = QRect(0, 0, self.width(), self.height())
        rectf = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rectf, 10, 10)
        painter.setClipPath(path)
        if self.pixmap():
            painter.drawPixmap(rect, self.pixmap())

        # Draw a black rectangle at the bottom of the image
        bottom_rect_height = int(self.height() * 0.08)
        bottom_rect = QRect(0, self.height() - bottom_rect_height, self.width(), bottom_rect_height)
        painter.fillRect(bottom_rect, QColor('black'))

        # Set the font and pen for drawing text
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.setPen(QColor('white'))

        # Draw the current airing episode (if anime is airing)
        if self.anime['airing']:
            current_episode_text = f"A{self.anime['last_aired_episode']}"
            current_episode_rect = QRect(0, self.height() - bottom_rect_height + 2, 25, bottom_rect_height - 4)
            painter.fillRect(current_episode_rect, QColor('green'))
            painter.drawText(current_episode_rect, Qt.AlignCenter, current_episode_text)

        # Draw the number of downloaded episodes
        downloaded_episodes_text = f"D{len(self.anime['episodes_downloaded'])}"
        downloaded_episodes_rect = QRect(self.width()-50, self.height() - bottom_rect_height + 2, 25, bottom_rect_height - 4)
        painter.fillRect(downloaded_episodes_rect, QColor('blue'))
        painter.drawText(downloaded_episodes_rect, Qt.AlignCenter, downloaded_episodes_text)

        # Draw the total number of episodes
        total_episodes_text = f"T{self.anime['total_episodes']}"
        total_episodes_rect = QRect(self.width()-25, self.height() - bottom_rect_height + 2, 25, bottom_rect_height - 4)
        painter.fillRect(total_episodes_rect, QColor('grey'))
        painter.drawText(total_episodes_rect, Qt.AlignCenter, total_episodes_text)

    def enterEvent(self, event):
        self.setStyleSheet(f"background-color: {cfg.themeColor.value.name()};")
        # Show delete button
        delete_button = PrimaryToolButton(FluentIcon.DELETE)
        delete_button.clicked.connect(self.on_delete_button_clicked)
        self.layout.addWidget(delete_button, alignment=Qt.AlignTop | Qt.AlignRight)

    def leaveEvent(self, event):
        self.setStyleSheet("background-color: transparent;")

        # Remove delete button
        delete_button = self.findChild(PrimaryToolButton)
        if delete_button:
            delete_button.deleteLater()

    def on_delete_button_clicked(self):
        self.delete_signal.emit(self.anime['id'])


class CustomListItemDelegate(ListItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        super().paint(painter, option, index)
        painter.save()
        painter.setPen(QPen(QColor(cfg.themeColor.value.name())))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()



class StackedWidget(QFrame):
    """ Stacked widget """

    currentWidgetChanged = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)
        self.view = PopUpAniStackedWidget(self)

        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.view)

        self.view.currentChanged.connect(
            lambda i: self.currentWidgetChanged.emit(self.view.widget(i)))

    def addWidget(self, widget):
        """ add widget to view """
        self.view.addWidget(widget)

    def setCurrentWidget(self, widget, popOut=True):
        widget.verticalScrollBar().setValue(0)
        if not popOut:
            self.view.setCurrentWidget(widget, duration=300)
        else:
            self.view.setCurrentWidget(
                widget, True, False, 200, QEasingCurve.InQuad)

    def setCurrentIndex(self, index, popOut=False):
        self.setCurrentWidget(self.view.widget(index), popOut)

class GalleryInterface(ScrollArea):
    """ Base interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setSpacing(30)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(36, 20, 36, 36)

        self.view.setObjectName('view')
        StyleSheet.GALLERY_INTERFACE.apply(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)


