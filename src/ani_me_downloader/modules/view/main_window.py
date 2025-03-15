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
from ..common.utils import get_r_path, compare_magnet_links


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

        self.downloadInterface.pauseResumeSignal.connect(self.toggle_torrent_state)
        self.downloadInterface.deleteSignal.connect(self.delete_torrent)
        self.downloadInterface.changePrioritySignal.connect(self.change_file_priority)

    def toggle_torrent_state(self, torrent_name):
        """Pause or resume a torrent based on its current state"""
        if hasattr(self, 'TorrentThread'):
            for torrent in self.torrents:
                if torrent.name == torrent_name:
                    current_status = torrent.status.lower()

                    if current_status == "paused":
                        if self.TorrentThread.resume_torrent(torrent_name):
                            self.showSuccess(f"Resumed torrent: {torrent_name}")
                    else:
                        if self.TorrentThread.pause_torrent(torrent_name):
                            self.showSuccess(f"Paused torrent: {torrent_name}")
                    break

    def delete_torrent(self, torrent_name, delete_files=False):
        """Remove a torrent and optionally its files"""
        if hasattr(self, 'TorrentThread'):
            if self.TorrentThread.remove_torrent(torrent_name, delete_files):
                message = f"Deleted torrent: {torrent_name}"
                if delete_files:
                    message += " with files"
                self.showSuccess(message)
                # Remove from UI
                for i, torrent in enumerate(self.torrents):
                    if torrent.name == torrent_name:
                        self.torrents.pop(i)
                        break
                self.saveTorrent()
            else:
                self.showError(f"Failed to delete torrent: {torrent_name}")

    def change_file_priority(self, torrent_name, file_index, priority):
        """Change the priority of a file in a torrent"""
        if hasattr(self, 'TorrentThread'):
            if self.TorrentThread.set_file_priorities(torrent_name, file_index, priority):
                self.showInfo(f"Changed priority for file in {torrent_name} to {priority}")
            else:
                self.showError(f"Failed to change priority for file in {torrent_name}")


    def startAnimeThread(self):
        if not self.animes:
            self.showInfo("Add Anime by Searching for it.")
            return

        self.AnimeThread = AnimeThread(self.animes)
        self.AnimeThread.sendFinished.connect(self.onFinished)
        for anime in self.animes:
            anime.infoSignal.connect(self.showInfo)
            anime.successSignal.connect(self.showSuccess)
            anime.errorSignal.connect(self.showError)
            anime.selectionSignal.connect(self.chooseTorrent)
            anime.addTorrentSignal.connect(self.addTorrent)
        self.AnimeThread.start()

    def startTorrentThread(self):
        if not self.torrents:
            return
        
        self.downloadInterface.set_torrent_data(self.torrents)
        
        self.TorrentThread = TorrentThread(self.torrents)
        self.TorrentThread.torrentComplete.connect(self.onTorrentComplete)
        self.TorrentThread.progressSignal.connect(self.downloadInterface.update_progress)
        self.TorrentThread.exitSignal.connect(self.onTorrentThreadExit)
        self.TorrentThread.errorSignal.connect(self.showError)
        #TODO: have a better way to handle this
        #self.TorrentThread.filesUpdatedSignal.connect(self.onFilesUpdated)
        self.TorrentThread.start()

    def initWindow(self):
        self.resize(850, 700)
        self.setMinimumWidth(600)
        self.logo = QIcon(get_r_path('logo.png'))
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
        # Stop the torrent thread properly to prevent crashes
        if hasattr(self, 'TorrentThread') and self.TorrentThread.isRunning():
            print("Stopping torrent thread...")
            self.TorrentThread.stop()

            # Don't wait on the GUI thread - just give it time to clean up
            import time
            time.sleep(0.5)  # Short delay to allow cleanup to start

        # Save torrent state
        self.saveTorrent()

        # Disconnect all signals to prevent callbacks after deletion
        if hasattr(self, 'TorrentThread'):
            try:
                self.TorrentThread.progressSignal.disconnect()
                self.TorrentThread.completedSignal.disconnect()
                self.TorrentThread.errorSignal.disconnect()
                self.TorrentThread.filesUpdatedSignal.disconnect()
            except:
                pass
    
        # Handle the standard close event
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

    def onTorrentComplete(self, to_remove):
        """Called when a torrent has completed downloading"""
        if to_remove:
            for torrent in to_remove:
                if hasattr(self, 'AnimeThread') and self.AnimeThread.isRunning():
                    # Queue the completed torrent info for later processing 
                    # when AnimeThread finishes
                    if not hasattr(self, 'completed_torrents'):
                        self.completed_torrents = []

                    self.completed_torrents.append(torrent)
                    self.showInfo(f"Queued {torrent.name} for processing after anime thread completes")
                else:
                    anime_id, magnet = torrent.anime_id, torrent.magnet
                    for anime in self.animes:
                        if anime.id == anime_id:
                            # Find which episode was downloading with this magnet link
                            for i, (episode, episode_magnet) in enumerate(anime.episodes_downloading):
                                if compare_magnet_links(episode_magnet, magnet):
                                    # Move from downloading to downloaded
                                    anime.episodes_downloaded.append(episode)
                                    anime.episodes_downloading.pop(i)
                                    self.showSuccess(f"Episode {episode} of {anime.name} completed downloading")
                                    break
                                
                            # Save the updated anime list
                            self.saveAnime()
                            break
                        
                # Remove the torrent regardless of whether AnimeThread is running
                self.delete_torrent(torrent.name, False)
    
    def onFilesUpdated(self, torrent_name):
        """Called when a torrent's file list has been updated"""
        #print(f"Files updated for {torrent_name}")
        # Update the UI if this is the currently selected torrent
        if self.downloadInterface.current_torrent == torrent_name:
            for i in range(self.downloadInterface.torrent_list.topLevelItemCount()):
                item = self.downloadInterface.torrent_list.topLevelItem(i)
                if item.text(0) == torrent_name:
                    self.downloadInterface.populate_detail_panel(item)
                    break
    
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
                    if hasattr(self, 'AnimeThread') and self.AnimeThread.isRunning():
                        self.animes.remove(anime)
                        self.anime_to_add.append(anime)
                    self.saveAnime()
                    break

    def addAnime(self, anime_info):
        new_anime = Anime(**anime_info)
        if hasattr(self, 'AnimeThread') and self.AnimeThread.isRunning():
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

        # Check if this torrent already exists by comparing magnet links
        for existing_torrent in self.torrents:
            if compare_magnet_links(existing_torrent.magnet, new_torrent.magnet):
                print(f"Torrent already exists: {new_torrent.name}")
                return

        if hasattr(self, 'TorrentThread') and self.TorrentThread.isRunning():
            print(f"Adding new torrent to queue: {new_torrent.name}")
            # Add to the pending list for the torrent thread
            self.torrent_to_add.append(new_torrent)

            # Also add to UI immediately
            self.torrents.append(new_torrent)
            self.downloadInterface.set_torrent_data([new_torrent])
        else:
            print(f"Torrent thread not running, adding torrent directly: {new_torrent.name}")
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
                if hasattr(self, 'AnimeThread') and self.AnimeThread.isRunning():
                    self.anime_to_remove.append(anime)
                self.animes.remove(anime)
                self.libraryInterface.update_grid(self.animes)
                break

        self.saveAnime()

    def onFinished(self, animes):
        self.animes = animes
        if hasattr(self, 'completed_torrents') and self.completed_torrents:
            for torrent in self.completed_torrents:
                anime_id, magnet = torrent.anime_id, torrent.magnet
                for anime in self.animes:
                    if anime.id == anime_id:
                        for i, (episode, episode_magnet) in enumerate(anime.episodes_downloading):
                            if compare_magnet_links(episode_magnet, magnet):
                                anime.episodes_downloaded.append(episode)
                                anime.episodes_downloading.pop(i)
                                self.showSuccess(f"Episode {episode} of {anime.name} completed downloading (from queue)")
                                break
                            
            # Clear the queue after processing
            self.completed_torrents = []

        if self.anime_to_remove:
            for anime in self.anime_to_remove:
                self.animes.remove(anime)
            self.anime_to_remove = []

        if self.anime_to_add:
            self.animes = self.anime_to_add + self.animes
            self.anime_to_add = []

        self.saveAnime()
        self.libraryInterface.update_grid(self.animes)

    def onTorrentThreadExit(self, torrents):
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
                print(f"Loaded {len(animes)} animes")
        except:
            animes = []

        try:
            with open(cfg.torrentFile.value, 'r') as f:
                data = json.load(f)
                torrents = [Torrent.from_dict(torrent_data) for torrent_data in data]
                print(f"Loaded {len(torrents)} torrents")
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
            # Remove duplicates before saving
            unique_torrents = []
            unique_hashes = set()
            
            for torrent in self.torrents:
                import re
                hash_match = re.search(r'btih:([a-fA-F0-9]+)', torrent.magnet)
                if hash_match:
                    torrent_hash = hash_match.group(1).lower()
                    if torrent_hash not in unique_hashes:
                        unique_hashes.add(torrent_hash)
                        unique_torrents.append(torrent)
                else:
                    # If we can't extract hash, just add it
                    unique_torrents.append(torrent)
            
            data = [torrent.to_dict() for torrent in unique_torrents]
            with open(cfg.torrentFile.value, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error in saveTorrent: {e}")