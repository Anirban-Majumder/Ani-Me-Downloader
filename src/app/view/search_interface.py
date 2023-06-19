# coding:utf-8
from PyQt5.QtWidgets import QLabel, QListWidgetItem
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import SearchLineEdit, MessageBox, StateToolTip

from .base_interface import BaseInterface
from ..common.style_sheet import StyleSheet


class SearchThread(QThread):
    searchFinished = pyqtSignal(list)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        from ..common.utils import get_anime_list, check_network
        if not check_network():
            self.statebox.setState(True)
            title = 'No Internet Connection'
            content = 'Please check your internet connection and try again'
            error_box = MessageBox(title, content, self)
            error_box.exec_()
            self.searchFinished.emit([])
        else:
            anime_list = get_anime_list(self.name)
            self.searchFinished.emit(anime_list)


class SearchInterface(BaseInterface):
    """ Search interface """
    addSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.vBoxLayout.addSpacing(100)
        self.label = QLabel("Ani-Me  Downloader")
        self.label.setObjectName('title')
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
        StyleSheet.SEARCH_INTERFACE.apply(self)


    def on_search_button_clicked(self):
        anime_name = self.search_field.text()
        self.statebox = StateToolTip("Searching",f"searching for {anime_name}",self)
        #show it in top center aligned
        self.statebox.move(int(self.width() / 2 - self.statebox.width() / 2), 10)
        self.statebox.show()

        self.search_thread = SearchThread(anime_name)
        self.search_thread.searchFinished.connect(self.on_search_finished)
        self.search_thread.start()


    def on_search_finished(self, anime_list):
        self.anime_list = anime_list
        from ..components.customdialog import ListDialog, AnimeDialog
        from ..common.utils import remove_invalid_chars, get_watch_url, get_season, os, download_path
        self.statebox.setState(True)
        self.clear_line()

        if len(self.anime_list) == 0:
            title = 'No results found'
            content = 'Try entering the proper name of the anime'
            error_box = MessageBox(title, content, self)
            error_box.exec_()
        else:
            self.message_box = ListDialog('Search Results',"Choose the anime form the list:", self)
            for anime in self.anime_list:
                item = QListWidgetItem(anime['title']['romaji'])
                item.setData(Qt.UserRole, anime)
                self.message_box.list_view.addItem(item)
            if self.message_box.exec_():
                selected_anime = self.message_box.list_view.currentItem().data(Qt.UserRole)
                name = remove_invalid_chars(selected_anime["title"]["romaji"])
                watch_url = get_watch_url(selected_anime["title"]["romaji"])
                season = get_season(watch_url)
                selected_anime["season"] = season
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

                    airing = selected_anime["status"] == 'RELEASING'
                    total_episodes = 24 if not selected_anime["episodes"] else selected_anime["episodes"]
                    output_dir = os.path.join(download_path, remove_invalid_chars(name))
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    episodes_to_download = list(range(selected_anime["from"], selected_anime["to"]+ 1))
                    info = {"name": name, "format": selected_anime["format"], "airing": airing,
                    "total_episodes": total_episodes, "img": selected_anime["coverImage"]["extraLarge"],
                    "output_dir": output_dir, "episodes_to_download": episodes_to_download,
                    "watch_url": watch_url, "id": selected_anime["id"], "season": season}

                    self.addSignal.emit(info)


    def clear_line(self):
        self.search_field.clear()
        self.search_field.setPlaceholderText('Enter the anime name')

