from PyQt5.QtCore import QThread, pyqtSignal
from ..common.utils import Constants, check_network
import libtorrent as lt
import time, os

class RunThread(QThread):
    runSignal = pyqtSignal()
    def __init__(self):
        super().__init__()

    def run(self):
        import time
        while True:
            time.sleep(600)
            self.runSignal.emit()

class AnimeThread(QThread):
    sendInfo = pyqtSignal(str)
    sendSuccess = pyqtSignal(str)
    sendError = pyqtSignal(str)
    sendTorrent = pyqtSignal(list)
    sendFinished = pyqtSignal(list)

    def __init__(self, animes):
        super().__init__()
        self.animes = animes

    def start_animes(self):
        for anime in self.animes:
            anime.infoSignal.connect(self.sendInfo)
            anime.successSignal.connect(self.sendSuccess)
            anime.errorSignal.connect(self.sendError)
            anime.torrentSignal.connect(self.sendTorrent)
            anime.start()

    def run(self):
        if not check_network():
            self.sendError.emit("There is something wrong with your Internet connection.")
            return
        if not check_network(Constants.qbit_url):
            from ..common.q_utils import start_qbittorrent
            if not start_qbittorrent():
                self.sendError.emit("There is something wrong with your qBittorrent.")
                return

        if not self.animes:
            self.sendInfo.emit("Add Anime by Searching for it.")
            return

        self.start_animes()
        self.sendFinished.emit(self.animes)
        self.sendInfo.emit("To see more details, please click the 'Library' button")
        import time
        from ..common.config import cfg
        cfg.animeLastChecked.value = int(time.time())
        cfg.save()



# ...existing code...

class TorrentThread(QThread):
    progressSignal = pyqtSignal(str, float, float)  # name, progress%, speed
    completedSignal = pyqtSignal(list)
    errorSignal = pyqtSignal(str)

    def __init__(self, torrents):
        super().__init__()
        self.torrents = torrents
        self._session = None
        self._handles = []
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            print("Initializing libtorrent session.")
            self._session = lt.session()
            self._session.listen_on(6881, 6891)
            print("Session listening on ports 6881-6891.")

            # Add each torrent with existing resume data if available
            for t in self.torrents:
                print(f"Adding torrent: {t.name}")
                params = lt.add_torrent_params()
                params.save_path = t.path
                if t.resume_data:
                    print(f"Resuming torrent: {t.name}")
                    params = lt.read_resume_data(t.resume_data)
                    params.save_path = t.path
                else:
                    print(f"Starting new torrent from magnet link: {t.name}")
                    params.url = t.magnet
                handle = self._session.add_torrent(params)
                self._handles.append((t, handle))
                print(f"Torrent added: {t.name}")

            # Download loop
            while not self._stop:
                st_all = []
                for torrent_obj, handle in self._handles:
                    s = handle.status()
                    progress = s.progress * 100
                    speed = s.download_rate / 1024
                    print(f"Progress - {torrent_obj.name}: {progress:.2f}% at {speed:.2f} KB/s")
                    self.progressSignal.emit(torrent_obj.name, progress, speed)
                    if s.is_seeding or s.progress >= 1.0:
                        torrent_obj.status = 'downloaded'
                        print(f"Torrent completed: {torrent_obj.name}")
                    st_all.append(s.is_seeding or s.progress >= 1.0)

                # Save resume data from alerts
                print("Processing alerts for resume data.")
                alerts = self._session.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.save_resume_data_alert):
                        tor_handle = alert.handle
                        for t_obj, h_obj in self._handles:
                            if h_obj == tor_handle:
                                t_obj.resume_data = lt.write_resume_data_buf(alert.params)
                                print(f"Resume data saved for torrent: {t_obj.name}")
                                break

                if all(st_all):
                    print("All torrents have been downloaded.")
                    break
                time.sleep(1)

            print("Emitting completedSignal.")
            self.completedSignal.emit(self.torrents)

        except Exception as e:
            print(f"Error in TorrentThread: {e}")
            self.errorSignal.emit(str(e))