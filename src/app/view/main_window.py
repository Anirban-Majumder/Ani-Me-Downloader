# coding: utf-8
import json, shutil
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QWidget,
                             QAction, QMenu, QSystemTrayIcon)

from qfluentwidgets import (NavigationInterface, NavigationItemPosition,
                            InfoBar, InfoBarIcon, qrouter)
from qfluentwidgets import FluentIcon as FIF

from .title_bar import CustomTitleBar
from .search_interface import SearchInterface
from .library_interface import LibraryInterface
from .download_interface import DownloadInterface
from .setting_interface import SettingInterface, cfg

from ..common.anime import Anime, constants
from ..components.frameless_window import FramelessWindow
from ..components.stackedwidget import StackedWidget
from ..common.style_sheet import StyleSheet
from ..common.utils import anime_file, check_network
from ..common.proxy_utils import get_proxies, check_proxies



class WorkerThread(QThread):
    sendUpdateinfo = pyqtSignal(str)
    sendUpdateerror = pyqtSignal(str)
    sendUpdatesuccess = pyqtSignal(str)
    sendListinfo = pyqtSignal(list)

    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.mainwindow.sendChoice.connect(self.onChoice)
        self.animes = []

    def load_anime_file(self):
        try:
            with open(anime_file, 'r') as f:
                data = json.load(f)
                animes = [Anime.from_dict(data) for data in data]
        except FileNotFoundError:
            self.senderror("There is something wrong with loading Anime file")
            animes = []
        return animes

    def start_animes(self):
        for anime in self.animes:
            anime.signal.infoSignal.connect(self.sendinfo)
            anime.signal.errorSignal.connect(self.senderror)
            anime.signal.successSignal.connect(self.sendsuccess)
            anime.signal.listSignal.connect(self.sendList)
            anime.start()

    def save_anime_file(self):
        if self.animes:
                data = [anime.to_dict() for anime in self.animes]
                with open(anime_file, 'w') as f:
                    json.dump(data, f, indent=4)

    def add_anime(self,anime):
        self.animes = self.load_anime_file()
        self.animes.insert(0, anime)
        self.save_anime_file()

    def remove_anime(self,id):
        self.animes = self.load_anime_file()
        for anime in self.animes:
            if anime.id == id:
                try:
                    shutil.rmtree(anime.output_dir)
                except Exception as e:
                    self.senderror(f"Sorry, can't delete the folder- {anime.output_dir}")
                self.animes.remove(anime)
        self.save_anime_file()

    def sendinfo(self,info):
        self.sendUpdateinfo.emit(info)

    def senderror(self,error):
        self.sendUpdateerror.emit(error)

    def sendsuccess(self,success):
        self.sendUpdatesuccess.emit(success)

    def sendList(self, list):
        self.sendListinfo.emit(list)

    def onChoice(self, list):
        if not list:
            return
        for anime in self.animes:
            if anime.id == list[0]:
                choice = list[1]
                anime.receiveData(choice)
                break
        self.save_anime_file()

    def run(self):
        if not check_network():
            self.senderror("There is something wrong with your Internet connection")
            return
        if not check_network(constants.qbit_url):
            self.senderror("There is something wrong with your qBittorrent")
            return

        self.animes = self.load_anime_file()
        if not self.animes:
            self.sendinfo("Add new anime by searching for it")
            return
        self.start_animes()
        self.save_anime_file()
        self.sendinfo("To see more details, please click the 'Library' button")
        get_proxies()
        check_proxies()


class MainWindow(FramelessWindow):
    sendChoice = pyqtSignal(list)
    def __init__(self):
        super().__init__()
        self.setTitleBar(CustomTitleBar(self))
        self.isIssue = False
        self.hBoxLayout = QHBoxLayout(self)
        self.widgetLayout = QHBoxLayout()

        self.stackWidget = StackedWidget(self)
        self.navigationInterface = NavigationInterface(self, True, False)

        # create sub interface
        self.searchInterface = SearchInterface(self)
        self.libraryInterface = LibraryInterface(self)
        self.downloadInterface = DownloadInterface(self)
        self.settingInterface = SettingInterface(self)

        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.initWindow()

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addLayout(self.widgetLayout)
        self.hBoxLayout.setStretchFactor(self.widgetLayout, 1)

        self.widgetLayout.addWidget(self.stackWidget)
        self.widgetLayout.setContentsMargins(0, 48, 0, 0)

        self.workerThread = WorkerThread(self)

        self.workerThread.sendUpdateinfo.connect(self.showInfo)
        self.workerThread.sendUpdatesuccess.connect(self.showSuccess)
        self.workerThread.sendUpdateerror.connect(self.showError)
        self.workerThread.sendListinfo.connect(self.choose_torrent)
        self.searchInterface.addSignal.connect(self.add_anime)
        self.libraryInterface.deleteSignal.connect(self.remove_anime)

        self.navigationInterface.displayModeChanged.connect(
            self.titleBar.raise_)
        self.titleBar.raise_()

    def initNavigation(self):
        # add navigation items
        self.addSubInterface(
            self.searchInterface, 'searchInterface', FIF.SEARCH, 'Search', NavigationItemPosition.TOP)
        self.addSubInterface(
            self.libraryInterface, 'libraryInterface', FIF.BOOK_SHELF, 'Library', NavigationItemPosition.TOP)
        self.navigationInterface.addSeparator()
        self.addSubInterface(
            self.downloadInterface, 'downloadInterface', FIF.DOWNLOAD, 'Download', NavigationItemPosition.TOP)
        self.addSubInterface(
            self.settingInterface, 'settingInterface', FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

        #!IMPORTANT: don't forget to set the default route key if you enable the return button
        qrouter.setDefaultRouteKey(self.stackWidget, self.searchInterface.objectName())

        self.stackWidget.currentWidgetChanged.connect(self.onCurrentWidgetChanged)
        self.navigationInterface.setCurrentItem(
            self.searchInterface.objectName())
        self.stackWidget.setCurrentIndex(0)

    def addSubInterface(self, interface: QWidget, objectName: str, icon, text: str, position=NavigationItemPosition.SCROLL):
        """ add sub interface """
        interface.setObjectName(objectName)
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=objectName,
            icon=icon,
            text=text,
            onClick=lambda t: self.switchTo(interface, t),
            position=position,
            tooltip=text
        )

    def initWindow(self):
        self.logo = QIcon('app/resource/logo.png')
        self.resize(900, 700)
        self.setMinimumWidth(600)
        self.setWindowIcon(self.logo)
        self.setWindowTitle('  Ani-Me  Downloader  ')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        StyleSheet.MAIN_WINDOW.apply(self)
        #self.workerThread.start()

    def create_tray_icon(self):
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

    def tempcloseEvent(self, event):
        self.hide()
        if cfg.minimizeToTray.value:
            event.ignore()

        else:
            self.tray_icon.hide()
            event.accept()

    def switchTo(self, widget, triggerByUser=True):
        self.stackWidget.setCurrentWidget(widget, not triggerByUser)

    def onCurrentWidgetChanged(self, widget: QWidget):
        self.navigationInterface.setCurrentItem(widget.objectName())
        qrouter.push(self.stackWidget, widget.objectName())

    def resizeEvent(self, e):
        self.titleBar.move(46, 0)
        self.titleBar.resize(self.width()-46, self.titleBar.height())

    def add_anime(self, result):
        new_anime = Anime(**result)
        self.switchTo(self.libraryInterface)
        self.libraryInterface.add_anime(new_anime.to_dict())
        self.workerThread.add_anime(new_anime)
        self.workerThread.start()

    def remove_anime(self, id):
        self.workerThread.remove_anime(id)

    def showInfo(self,info):
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

    def showFirstTime(self):
        print("First Time")
        from qfluentwidgets import MessageBox
        import os
        user = os.getlogin()
        title=f"Welcome {user} to Ani-Me Downloader"
        text="""We're glad you're here. By using this application, you agree to the following terms and conditions:

1. Introduction :
These Terms of Service govern your use of ANI-me-downloader. By accessing or using this application, you agree to be bound by these Terms and all applicable laws and regulations.

2. Purpose
The core aim of ANI-me-downloader is to co-relate automation and efficiency to extract what is provided to a user on the internet. All content available through the application is hosted by external non-affiliated sources.

3. Content
All content served through this application is publicly accessible. ANI-me-downloader has no control over the content it serves, and any use of copyrighted content from the providers is at the user's own risk.

4. User Conduct
You agree to use ANI-me-downloader in a manner that is lawful, respectful, and in accordance with these Terms. You may not use this application in any way that could harm, disable, or impair this application or interfere with any other party's use and enjoyment of the application.

5. Disclaimer
This project is to be used at the user's own risk, based on their government and laws. Any copyright infringements or DMCA in this project's regards are to be forwarded to the associated site by the associated notifier of any such claims.

6. Limitation of Liability
In no event shall ANI-me-downloader or its developers be liable for any damages (including, without limitation, damages for loss of data or profit, or due to business interruption) arising out of the use or inability to use the materials on ANI-me-downloader's application, even if ANI-me-downloader or an authorized representative has been notified orally or in writing of the possibility of such damage.

Thank you for using ANI-me-downloader!
"""
        message = MessageBox(title, text, self)
        print(message.contentLabel.width())
        if message.exec_():
            title=f"Hello, {user} here's a quick tour of Ani-Me Downloader"
            text="""
You need to have a qbittorrent installed on your system to use this application.
If you don't have one, you can download it from here: https://www.qbittorrent.org/download.php
After you are done with the installation, you need to configure the application to use it.
To do that, go to settings and click on the 'Web UI' tab. Then Click on web user interface checkbox and turn it on.
After that, Click on Bypass authentication for clients on localhost checkbox and click on apply.
(Optional) You really should set a username and password for your qbittorrent web ui so that no one else can access it.

Coming back to the tour :|
You can search for the things to download from the search tab.
then you can choose the the things from list of things that you searched for.
After that, you can verify all the info and click on okay to start.
And Voila! You're done. You can see the progress in the library tab.
"""
            message2 = MessageBox(title, text, self)
            if message2.exec_():
                cfg.set('firstTime', False)
                print(cfg.firstTime.value)
            else:
                exit()
        else:
            exit()

    def choose_torrent(self, list):
        from ..components.customdialog import ListDialog
        from PyQt5.QtWidgets import QListWidgetItem
        self.torrent_box = ListDialog('Torrent Results',"Choose the torrent form the list:", self)
        id, torrent_list = list[0], list[1]
        for torrent in torrent_list:
            text = f"{torrent[0]} \n {torrent[2]}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, torrent)
            self.torrent_box.list_view.addItem(item)

        if self.torrent_box.exec_():
            selected_torrent = self.torrent_box.list_view.currentItem().data(Qt.UserRole)
            self.sendChoice.emit([id,selected_torrent])
        else:
            self.sendChoice.emit([])
