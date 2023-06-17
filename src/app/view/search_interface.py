# coding:utf-8
from PyQt5.QtWidgets import QLabel, QListWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import SearchLineEdit, MessageBox, StateToolTip

from ..common.utils import get_anime_list

from .base_interface import BaseInterface

class SearchInterface(BaseInterface):
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
        from ..components.customdialog import ListDialog, AnimeDialog
        self.anime_list = get_anime_list(anime_name)
        self.statebox.setState(True)
        self.message_box = ListDialog('Search Results',"Choose the anime form the list:", self)
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
                    selected_anime['episodes'] = infobox.episodes.value()
                    selected_anime['status'] = infobox.status_combobox.currentText()
                    selected_anime['season'] = infobox.season.value()
                    if selected_anime['status'] == 'RELEASING':
                        selected_anime['nextAiringEpisode'] = infobox.next_airing_episode.value()
                    else:
                        selected_anime['nextAiringEpisode'] = None
                    selected_anime['from'] = infobox.from_download.value()
                    selected_anime['to'] = infobox.to_download.value()
                    self.addSignal.emit(selected_anime)


    def clear_line(self):
        self.search_field.clear()
        self.search_field.setPlaceholderText('Enter the anime name')

