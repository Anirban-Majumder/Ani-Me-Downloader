# coding:utf-8
import os

from PyQt5.QtWidgets import QLabel, QListWidgetItem
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from qfluentwidgets import SearchLineEdit, MessageBox, StateToolTip

from .base_interface import BaseInterface
from ..common.style_sheet import StyleSheet
from ..components.customdialog import ListDialog, AnimeDialog
from ..common.config import cfg
from ..common.utils import (remove_non_alphanum, clean_title,
                            get_watch_url, get_season)


class SearchThread(QThread):
    searchFinished = pyqtSignal(list)

    def __init__(self, anime_name):
        super().__init__()
        self.anime_name = anime_name

    def run(self):
        from ..common.utils import get_anime_list, check_network
        if not check_network():
            print("No Internet")
            self.searchFinished.emit(["No Internet"])
        else:
            print("Searching")
            anime_list = get_anime_list(self.anime_name)
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
        self.statebox = StateToolTip("Searching", f"searching for {anime_name}", self)
        self.statebox.move(int(self.width() / 2 - self.statebox.width() / 2), 10)
        self.statebox.show()

        self.search_thread = SearchThread(anime_name)
        self.search_thread.searchFinished.connect(self.on_search_finished)
        self.search_thread.start()


    def on_search_finished(self, anime_list):
        self.anime_list = anime_list
        self.statebox.setState(True)
        self.clear_line()

        if len(self.anime_list) == 0:
            title = 'No results found'
            content = 'Try entering the proper name of the anime'
            error_box = MessageBox(title, content, self)
            error_box.exec_()
        elif self.anime_list[0] == "No Internet":
            title = 'No Internet Connection'
            content = 'Please check your internet connection and try again'
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
                if selected_anime['status'] == "NOT_YET_RELEASED":
                    title="Sorry this anime is not yet released"
                    content = "Please try again later, when the anime is airring."
                    error_box = MessageBox(title, content, self)
                    error_box.exec_()
                    return

                anime_name = selected_anime["title"]["romaji"]
                name = remove_non_alphanum(anime_name)
                search_name =  clean_title(anime_name)
                watch_url = get_watch_url(anime_name)
                season = get_season(watch_url)
                selected_anime["season"] = season
                selected_anime["title"]["romaji"] = search_name
                print(selected_anime)
                infobox=AnimeDialog(selected_anime,self)
                if infobox.exec_():
                    search_name = infobox.title_label.text()
                    total_episodes = infobox.episodes.value()
                    season = infobox.season.value()
                    from_ep = infobox.from_download.value()
                    to_ep = infobox.to_download.value()
                    batch_download = True if infobox.download_type.currentText() == "Full" else False
                    selected_anime['status'] = infobox.status_combobox.currentText()
                    airing = selected_anime["status"] == 'RELEASING'
                    if airing:
                        last_aired_episode = infobox.next_airing_episode.value()
                        last_aired_episode-=1
                    else:
                        last_aired_episode = total_episodes
                    next_eta = selected_anime['nextAiringEpisode']['airingAt'] if selected_anime['nextAiringEpisode'] else 0
                    output_dir = os.path.join(cfg.downloadFolder.value, name)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                    episodes_to_download = list(range(from_ep, to_ep+ 1))
                    result = {"name": name, "search_name": search_name, "format": selected_anime["format"], "airing": airing, "next_eta": next_eta,
                    "total_episodes": total_episodes, "img": selected_anime["coverImage"]["extraLarge"], "last_aired_episode": last_aired_episode,
                    "output_dir": output_dir, "episodes_to_download": episodes_to_download, "season": season,
                    "watch_url": watch_url, "id": selected_anime["id"], "idMal":selected_anime["idMal"], "batch_download": batch_download}
                    #print(result)
                    self.addSignal.emit(result)


    def clear_line(self):
        self.search_field.clear()
        self.search_field.setPlaceholderText('Enter the anime name')

