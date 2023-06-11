# coding:utf-8
from PyQt5.QtWidgets import QLabel, QListWidgetItem, QVBoxLayout, QFormLayout,QHBoxLayout
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QEvent, pyqtSignal
from qfluentwidgets import SearchLineEdit, MessageBox, ListWidget, LineEdit, SpinBox, ComboBox, StateToolTip
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox

from ..common.utils import get_anime_list, get_img

from .base_interface import GalleryInterface, CustomListItemDelegate

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
        self.title_label = LineEdit()
        self.title_label.setText(anime['title']['romaji'])
        form_layout.addRow('Title:', self.title_label)

        # Add a spin box for the next airing episode (only enabled if status is RELEASING)
        self.next_airing_episode_spinbox = SpinBox()
        self.next_airing_episode_spinbox.setEnabled(anime['status'] == 'RELEASING')
        if anime["status"] == 'RELEASING':
            self.next_airing_episode_spinbox.setValue(anime['nextAiringEpisode']['episode'])
            form_layout.addRow('Next Airing Episode:', self.next_airing_episode_spinbox)

        # Add a spin box for the number of episodes
        self.episodes_spinbox = SpinBox()
        self.episodes_spinbox.setValue(anime['episodes'])
        form_layout.addRow('Total Episodes:', self.episodes_spinbox)



        # Add a combo box for the status
        self.status_combobox = ComboBox(self)
        self.status_combobox.addItems(['FINISHED', 'RELEASING', 'NOT_YET_RELEASED'])
        self.status_combobox.setCurrentText(anime['status'])
        self.status_combobox.currentTextChanged.connect(lambda text: self.next_airing_episode_spinbox.setEnabled(text == 'RELEASING'))
        form_layout.addRow('Status:', self.status_combobox)

        # Add a spin box for the season
        self.season_spinbox = SpinBox()
        self.season_spinbox.setValue(1)
        form_layout.addRow('Season:', self.season_spinbox)


    def load_img(self,url,label):
        pixmap = get_img(url)
        scaled_pixmap = pixmap.scaled(self.img_size[0], self.img_size[1])
        label.setPixmap(scaled_pixmap)

    def eventFilter(self, obj, e: QEvent):
      if obj is self.window():
          if e.type() == QEvent.Resize:
              self._adjustText()

      return super().eventFilter(obj, e)



class SearchInterface(GalleryInterface):
    """ Search interface """
    addSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.vBoxLayout.addSpacing(100)
        self.label = QLabel("Ani-Me Downloader")
        font = self.label.font()
        font.setPointSize(24) # Set font size
        font.setBold(True) # Set font to bold
        font.setItalic(True) # Set font to italic
        self.label.setFont(font)
        self.label.setStyleSheet("color: #ffffff")
        self.label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.label, 0, Qt.AlignCenter)

        self.vBoxLayout.addSpacing(50)

        self.search_field = SearchLineEdit(self)
        self.search_field.setPlaceholderText('Enter the anime name')
        self.search_field.setFixedSize(400, 40)
        self.search_field.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.search_field, 0, Qt.AlignCenter)
        self.search_field.searchSignal.connect(self.on_search_button_clicked)
        self.search_field.clearSignal.connect(lambda: self.clear_line)
        self.search_field.returnPressed.connect(self.on_search_button_clicked)


    def on_search_button_clicked(self):
        anime_name = self.search_field.text()
        self.statebox = StateToolTip("Searching",f"searching for {anime_name}",self)
        #show it in top center aligned
        self.statebox.move(int(self.width() / 2 - self.statebox.width() / 2), 10)
        self.statebox.show()
        self.anime_list = get_anime_list(anime_name)
        self.statebox.setState(True)
        self.message_box = ListDialog('Search Results',"Choose the anime form the list:"+" "*50, self)
        for anime in self.anime_list:
            item = QListWidgetItem(anime['title']['romaji'])
            item.setData(Qt.UserRole, anime)
            self.message_box.list_view.addItem(item)

        self.clear_line()
        if len(self.anime_list) == 0:
            title = 'No results found'
            content = 'Try entering the proper name of the anime'
            error_box = MessageBox(title, content, self)
            error_box.exec_()
        else:
            if self.message_box.exec_():
                selected_anime = self.message_box.list_view.currentItem().data(Qt.UserRole)
                infobox=AnimeDialog(selected_anime,self)
                infobox.contentLabel.setText("Make sure this info is correct and make corrections as necessary"+" "*40)
                if infobox.exec_():
                    selected_anime['title']['romaji'] = infobox.title_label.text()
                    selected_anime['episodes'] = infobox.episodes_spinbox.value()
                    selected_anime['status'] = infobox.status_combobox.currentText()
                    selected_anime['season'] = infobox.season_spinbox.value()
                    if infobox.next_airing_episode_spinbox.isEnabled():
                        selected_anime['nextAiringEpisode'] = infobox.next_airing_episode_spinbox.value()
                    else:
                        selected_anime['nextAiringEpisode'] = None
                    self.addSignal.emit(selected_anime)


    def clear_line(self):
        self.search_field.clear()
        self.search_field.setPlaceholderText('Enter the anime name')

