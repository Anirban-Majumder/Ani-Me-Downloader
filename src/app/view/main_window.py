# coding: utf-8
import json, shutil
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QHBoxLayout,
                             QAction, QMenu, QSystemTrayIcon)

from qfluentwidgets import (NavigationInterface, NavigationItemPosition,
                            InfoBar, InfoBarIcon, FluentWindow)
from qfluentwidgets import FluentIcon as FIF

from .workers import *
from .title_bar import CustomTitleBar
from .search_interface import SearchInterface
from .library_interface import LibraryInterface
from .download_interface import DownloadInterface
from .setting_interface import SettingInterface, cfg

from ..common.anime import Anime
from ..common.torrent import Torrent
from ..common.style_sheet import StyleSheet


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initLayout()

        self.animes, self.torrents = self.load()
        self.anime_to_add = []
        self.anime_to_remove = []
        self.torrent_to_add = []
        self.searchingBox = None
        self.searchInterface = SearchInterface(self)
        self.libraryInterface = LibraryInterface(self)
        self.downloadInterface = DownloadInterface(self)
        self.settingInterface = SettingInterface(self)

        self.initNavigation()
        self.initSignals()
        self.initWindow()

    def initLayout(self):
        self.setTitleBar(CustomTitleBar(self))
        self.hBoxLayout.removeWidget(self.navigationInterface)
        self.widgetLayout.removeWidget(self.navigationInterface)
        self.navigationInterface.setParent(None)
        self.navigationInterface = NavigationInterface(self, showReturnButton=False)
        self.widgetLayout = QHBoxLayout()

        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addLayout(self.widgetLayout)
        self.hBoxLayout.setStretchFactor(self.widgetLayout, 1)

        self.widgetLayout.addWidget(self.stackedWidget)
        self.widgetLayout.setContentsMargins(0, 48, 0, 0)

        self.navigationInterface.displayModeChanged.connect(self.titleBar.raise_)
        self.titleBar.raise_()

    def initNavigation(self):
        self.searchInterface.setObjectName('searchInterface')
        self.libraryInterface.setObjectName('libraryInterface')
        self.downloadInterface.setObjectName('downloadInterface')
        self.settingInterface.setObjectName('settingInterface')

        self.addSubInterface(self.searchInterface, FIF.SEARCH, 'Search')
        self.addSubInterface(self.libraryInterface, FIF.BOOK_SHELF, 'Library')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.downloadInterface, FIF.DOWNLOAD, 'Download')
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

    def initSignals(self):
        self.runThread = RunThread()
        self.runThread.runSignal.connect(self.startAnimeThread)
        self.runThread.start()
        self.searchInterface.addSignal.connect(self.addAnime)
        self.libraryInterface.deleteSignal.connect(self.removeAnime)

    def startAnimeThread(self):
        self.AnimeThread = AnimeThread(self.animes)
        self.AnimeThread.sendInfo.connect(self.showInfo)
        self.AnimeThread.sendSuccess.connect(self.showSuccess)
        self.AnimeThread.sendError.connect(self.showError)
        self.AnimeThread.sendTorrent.connect(self.chooseTorrent)
        self.AnimeThread.sendFinished.connect(self.onFinished)

        self.AnimeThread.start()

    def startTorrentThread(self):
        self.TorrentThread = TorrentThread(self.torrents)
        self.TorrentThread.progressSignal.connect(self.update_download_progress)
        self.TorrentThread.completedSignal.connect(self.onCompleted)
        self.TorrentThread.errorSignal.connect(self.showError)
        
        self.TorrentThread.start()

    def initWindow(self):
        self.resize(850, 700)
        self.setMinimumWidth(600)
        self.logo = QIcon('app/resource/logo.png')
        self.setWindowIcon(self.logo)
        self.setWindowTitle('  Ani-Me  Downloader  ')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width()  // 2, h // 2 - self.height() // 2)

        StyleSheet.MAIN_WINDOW.apply(self)
        self.startAnimeThread()
        self.startTorrentThread()

    def __create_tray_icon(self):
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.showNormal)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.quit)

        tray_menu = QMenu(self)
        tray_menu.addAction(show_action)
        tray_menu.addAction(exit_action)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.logo)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        self.saveTorrent()
        super().closeEvent(event)

    def __tempcloseEvent(self, event):
        self.hide()
        if cfg.minimizeToTray.value:
            event.ignore()

        else:
            self.tray_icon.hide()
            event.accept()

    def showInfo(self,info):
        if "searching" in info:
            from qfluentwidgets import StateToolTip
            self.searchingBox = StateToolTip("Searching","searching for torrents",self)
            self.searchingBox.move(int(self.width()-(self.searchingBox.width()+10)), int(self.height()-(self.searchingBox.height()+10)))
            self.searchingBox.show()
            return

        if  cfg.showNotification.value:
            w = InfoBar(
                icon=InfoBarIcon.INFORMATION,
                title='Info',
                content=info,
                duration=6000,
                parent=self
            )
            w.show()

    def showError(self,error):
        if "searching" in error:
            if self.searchingBox:
                self.searchingBox.setState(True)
                return

        w = InfoBar(
            icon=InfoBarIcon.ERROR,
            title='Error',
            content=error,
            duration=6000,
            parent=self
        )
        w.show()

    def showSuccess(self,success):
        if  cfg.showNotification.value:
            w = InfoBar(
                icon=InfoBarIcon.SUCCESS,
                title='Success',
                content=success,
                duration=6000,
                parent=self
            )
            w.show()

    def update_download_progress(self, name, progress, speed):
        """Update the download interface with progress."""
        self.downloadInterface.update_progress(name, progress, speed)
    
    def showFirstTime(self):
        from qfluentwidgets import MessageBox
        from ..common.constants import Constants
        import os
        user = os.getlogin()
        title=f"Welcome {user} to Ani-Me Downloader"
        message = MessageBox(title, Constants.terms_text, self)
        message.yesButton.setText("I Agree")
        message.cancelButton.setText("I Disagree")
        if message.exec_():
            title=f"Hello, {user} here's a quick tour of Ani-Me Downloader"
            message2 = MessageBox(title, Constants.about_text0, self)
            message2.yesButton.setText("Okay")
            from ..common.q_utils import get_qbittorrent_url
            if message2.exec_():
                title="PLEASE READ CAREFULLY (STEP 1)"
                message3 = MessageBox(title, Constants.about_text1, self)
                message3.yesButton.setText("Okay")
                url = get_qbittorrent_url()
                from PyQt5.QtCore import QUrl
                from PyQt5.QtGui import QDesktopServices
                if message3.exec_():
                    QDesktopServices.openUrl(QUrl(url))
                    title="PLEASE READ CAREFULLY (STEP 2)"
                    message4 = MessageBox(title, Constants.about_text2, self)
                    message4.yesButton.setText("Okay")
                    if message4.exec_():
                        title=f"{user} You sure You have Qbittorrent installed?"
                        message5 = MessageBox(title, " ", self)
                        message5.yesButton.setText("Yes")
                        message5.cancelButton.setText("No")
                        if message5.exec_():
                            cfg.set(cfg.firstTime, False)

    def chooseTorrent(self, list):
        from ..components.customdialog import ListDialog
        from PyQt5.QtWidgets import QListWidgetItem
        title = 'Torrent Results, Please Choose:'
        content = 'Sorry, we couldnt figure out which torrent to download. Please choose one from the list below:'
        self.torrent_box = ListDialog(title, content, self)
        id, torrent_list = list[0], list[1]
        for torrent in torrent_list:
            text = f"{torrent[2]} || {torrent[0]}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, torrent)
            self.torrent_box.list_view.addItem(item)

        if self.torrent_box.exec_():
            selected_torrent = self.torrent_box.list_view.currentItem().data(Qt.UserRole)
            for anime in self.animes:
                if anime.id == id:
                    anime.receive_data(selected_torrent)
                    if self.AnimeThread.isRunning():
                        self.animes.remove(anime)
                        self.anime_to_add.append(anime)
                    self.saveAnime()
                    break

    def addAnime(self, anime_info):
        new_anime = Anime(**anime_info)
        if self.AnimeThread.isRunning():
            self.anime_to_add.append(new_anime)
            self.switchTo(self.libraryInterface)
            self.libraryInterface.update_grid(self.anime_to_add + self.animes)
        else:
            self.animes.insert(0, new_anime)
            self.switchTo(self.libraryInterface)
            self.libraryInterface.update_grid(self.animes)
            self.saveAnime()
            self.startAnimeThread()

    def addTorrent(self, torrent_info):
        new_torrent = Torrent(**torrent_info)
        if self.TorrentThread.isRunning():
            self.torrent_to_add.append(new_torrent)
        else:
            self.torrents.insert(0, new_torrent)
            self.saveTorrent()
            self.startTorrentThread()

    def removeAnime(self, id):
        for anime in self.animes:
            if anime.id == id:
                try:
                    shutil.rmtree(anime.output_dir)
                except:
                    self.showError(f"Sorry, can't delete the folder {anime.output_dir} cause Something else is still using It!!!")
                if self.AnimeThread.isRunning():
                    self.anime_to_remove.append(anime)
                self.animes.remove(anime)
                self.libraryInterface.update_grid(self.animes)
                break

        self.saveAnime()

    def onFinished(self, animes):
        self.animes = animes

        if self.anime_to_remove:
            for anime in self.anime_to_remove:
                self.animes.remove(anime)
            self.anime_to_remove = []

        if self.anime_to_add:
            self.animes = self.anime_to_add + self.animes
            self.anime_to_add = []

        self.saveAnime()
        self.libraryInterface.update_grid(self.animes)

    def onCompleted(self, torrents):
        self.torrents = torrents

        if self.torrent_to_add:
            self.torrents = self.torrent_to_add + self.torrents
            self.torrent_to_add = []

        self.saveTorrent()

    def load(self):
        try:
            with open(cfg.animeFile.value, 'r') as f:
                data = json.load(f)
                animes = [Anime.from_dict(data) for data in data]
        except:
            animes = []

        try :
            with open(cfg.torrentFile.value, 'r') as f:
                data = json.load(f)
                torrents = [Torrent.from_dict(data) for data in data]
                torrents =[]
        except:
            torrents = []
        return animes, torrents

    def saveAnime(self):
        try:
            data = [anime.to_dict() for anime in self.animes]
            with open(cfg.animeFile.value, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            print("Error in saveAnime")

    def saveTorrent(self):
        try:
            data = [torrent.to_dict() for torrent in self.torrents]
            with open(cfg.torrentFile.value, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            print("Error in saveTorrent")