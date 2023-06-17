from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import  QPainter, QPen, QColor
from PyQt5.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QVBoxLayout,
                             QStyleOptionViewItem, QFormLayout)
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox
from qfluentwidgets import (ListWidget, LineEdit, SpinBox, ComboBox, ListItemDelegate, isDarkTheme)


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

        # Create a layout for the message box
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
        if obj is self.window():
            if e.type() == QEvent.Resize:
                self._adjustText()

        return super().eventFilter(obj, e)


class AnimeDialog(MaskDialogBase, Ui_MessageBox):
    def __init__(self, anime, parent=None):
        super().__init__(parent)
        self._setUpUi("Verify and Confirm Info", " ", self.widget)
        self.yesButton.setText("Confirm")

        # Create a layout for the message box
        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)
        self.message_box_layout = QHBoxLayout()
        self.vBoxLayout.insertLayout(1, self.message_box_layout)

        # Show the cover image on the left side of the dialog
        cover_image_label = QLabel()
        self.message_box_layout.addWidget(cover_image_label, Qt.AlignLeft)
        url = anime['coverImage']['extraLarge']
        self.img_size = (164, 240)
        self.load_img(url, cover_image_label)

        # Create a form layout for the anime info on the right side of the dialog
        form_layout = QFormLayout()
        self.message_box_layout.addLayout(form_layout, Qt.AlignRight)

        # Add the anime title (not editable)
        self.title_label = LineEdit(self)
        self.title_label.setText(anime['title']['romaji'])
        form_layout.addRow('Title:', self.title_label)
        form_layout.setContentsMargins(30,30,30,30)
        form_layout.setSpacing(8)

        # Add a spin box for the season
        self.season = SpinBox(self)
        self.season.setValue(1)
        form_layout.addRow('Season:', self.season)

        # Add a spin box for the next airing episode (only enabled if status is RELEASING)
        if anime["status"] == 'RELEASING':
            self.next_airing_episode = SpinBox(self)
            self.next_airing_episode.setEnabled(anime['status'] == 'RELEASING')
            self.next_airing_episode.setValue(anime['nextAiringEpisode']['episode'])
            form_layout.addRow('Next Airing Episode:', self.next_airing_episode)

        # Add a spin box for the number of episodes
        self.episodes = SpinBox(self)
        self.episodes.setValue(anime['episodes'])
        form_layout.addRow('Total Episodes:', self.episodes)

        # Add a combo box for the status
        self.status_combobox = ComboBox(self)
        self.status_combobox.addItems(['FINISHED', 'RELEASING', 'NOT_YET_RELEASED'])
        self.status_combobox.setCurrentText(anime['status'])
        self.status_combobox.currentTextChanged.connect(lambda text: self.next_airing_episode.setEnabled(text == 'RELEASING'))
        form_layout.addRow('Status:', self.status_combobox)

        self.from_download = SpinBox(self)
        self.from_download.setValue(1)
        form_layout.addRow('Download from episode:', self.from_download)

        self.to_download = SpinBox(self)
        self.to_download.setValue(anime['episodes'])
        form_layout.addRow('Download to episode:           ', self.to_download)


    def load_img(self,url,label):
        pixmap = get_img(url)
        scaled_pixmap = pixmap.scaled(self.img_size[0], self.img_size[1])
        label.setPixmap(scaled_pixmap)

    def eventFilter(self, obj, e: QEvent):
      if obj is self.window():
          if e.type() == QEvent.Resize:
              self._adjustText()

      return super().eventFilter(obj, e)
