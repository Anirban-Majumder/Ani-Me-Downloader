# coding: utf-8
import json, shutil, time
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QEventLoop
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget

from qfluentwidgets import (NavigationInterface, NavigationItemPosition,
                            InfoBar, InfoBarIcon, InfoBarPosition, qrouter)
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
from ..common.utils import get_anime_detail, anime_file, check_network
from ..common.proxy_utils import get_proxies, check_proxies



class WorkerThread(QThread):
    sendUpdateinfo = pyqtSignal(str)
    sendUpdateerror = pyqtSignal(str)
    sendUpdatesuccess = pyqtSignal(str)
    sendListinfo = pyqtSignal(list)

    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.wait_for_res = False

    def load_anime_file(self):
        try:
            with open(anime_file, 'r') as f:
                data = json.load(f)
                animes = [Anime.from_dict(data) for data in data]
        except FileNotFoundError:
            self.senderror("There is something wrong with loading Anime file")
            animes = []
        return animes

    def start_animes(self,animes):
        for anime in animes:
            anime.signal.infoSignal.connect(self.sendinfo)
            anime.signal.errorSignal.connect(self.senderror)
            anime.signal.successSignal.connect(self.sendsuccess)
            anime.signal.listSignal.connect(self.sendList)
            self.mainwindow.sendDataSignal.connect(anime.receiveData)
            anime.start()
            if self.wait_for_res:
                loop = QEventLoop()
                self.mainwindow.sendDataSignal.connect(loop.quit)
                loop.exec_()
            else:
                time.sleep(3)

    def save_anime_file(self,animes):
        if animes:
                data = [anime.to_dict() for anime in animes]
                with open(anime_file, 'w') as f:
                    json.dump(data, f, indent=4)

    def add_anime(self,anime):
        animes = self.load_anime_file()
        animes.insert(0, anime)
        self.save_anime_file(animes)

    def remove_anime(self,id):
        animes = self.load_anime_file()
        for anime in animes:
            if anime.id == id:
                try:
                    shutil.rmtree(anime.output_dir)
                except Exception as e:
                    self.senderror(f"Sorry, can't delete the folder- {anime.output_dir}")
                animes.remove(anime)
        self.save_anime_file(animes)

    def sendinfo(self,info):
        self.sendUpdateinfo.emit(info)

    def senderror(self,error):
        self.sendUpdateerror.emit(error)

    def sendsuccess(self,success):
        self.sendUpdatesuccess.emit(success)

    def sendList(self, list):
        self.sendListinfo.emit(list)
        self.wait_for_res = True

    def run(self):
        if not check_network():
            self.senderror("There is something wrong with your Internet connection")
            return
        if not check_network(constants.qbit_url):
            self.senderror("There is something wrong with your qBittorrent")
            return

        animes = self.load_anime_file()
        if not animes:
            self.sendinfo("Add new anime by searching for it")
            return
        self.start_animes(animes)
        self.save_anime_file(animes)
        self.sendinfo("To see more details, please click the 'Library' button")
        #check_proxies()

class MainWindow(FramelessWindow):
    sendDataSignal = pyqtSignal(list)
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
        self.resize(900, 700)
        self.setMinimumWidth(600)
        self.setWindowIcon(QIcon('app/resource/logo.png'))
        self.setWindowTitle('  Ani-Me  Downloader  ')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        StyleSheet.MAIN_WINDOW.apply(self)
        self.workerThread.start()

    def switchTo(self, widget, triggerByUser=True):
        self.stackWidget.setCurrentWidget(widget, not triggerByUser)

    def onCurrentWidgetChanged(self, widget: QWidget):
        self.navigationInterface.setCurrentItem(widget.objectName())
        qrouter.push(self.stackWidget, widget.objectName())

    def resizeEvent(self, e):
        self.titleBar.move(46, 0)
        self.titleBar.resize(self.width()-46, self.titleBar.height())

    def add_anime(self, anime):
        result = get_anime_detail(anime)
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
                position=InfoBarPosition.BOTTOM_RIGHT,
                title='Info',
                content=info,
                duration=3000,
                parent=self
            )
            w.show()

    def showError(self,error):
        w = InfoBar(
            icon=InfoBarIcon.ERROR,
            title='Error',
            content=error,
            duration=5000,
            parent=self
        )
        w.show()

    def showSuccess(self,success):
        if  cfg.showNotification.value:
            w = InfoBar(
                icon=InfoBarIcon.SUCCESS,
                position=InfoBarPosition.BOTTOM_RIGHT,
                title='Success',
                content=success,
                duration=3000,
                parent=self
            )
            w.show()

    def showFirst(self):
        #show disclaimer
        #show onboarding/into
        pass

    def choose_torrent(self, torrent_list):
        from ..components.customdialog import ListDialog
        from PyQt5.QtWidgets import QListWidgetItem
        self.torrent_box = ListDialog('Torrent Results',"Choose the torrent form the list:", self)
        for torrent in torrent_list:
            item = QListWidgetItem(torrent[0])
            item.setData(Qt.UserRole, torrent)
            self.torrent_box.list_view.addItem(item)

        if self.torrent_box.exec_():
            selected_torrent = self.torrent_box.list_view.currentItem().data(Qt.UserRole)
            self.sendDataSignal.emit(selected_torrent)
        else:
            self.sendDataSignal.emit([])
