from PyQt5.QtCore import QThread, pyqtSignal
from ..common.utils import Constants, check_network


class RunThread(QThread):
    runSignal = pyqtSignal()
    def __init__(self):
        super().__init__()

    def run(self):
        import time
        while True:
            time.sleep(600)
            self.runSignal.emit()

class WorkerThread(QThread):
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
