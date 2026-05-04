"""
A simple and beautiful anime downloader and streamer.
"""
import os
import sys
import warnings

# Suppress SIP deprecation warnings
warnings.filterwarnings("ignore", message=".*sipPyTypeDict.*", category=DeprecationWarning)

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

from .config.config import cfg
from .config.paths import data_dir
from .persistence.anime_repo import AnimeRepository
from .persistence.torrent_repo import TorrentRepository
from .services.coordinator import Coordinator
from .state.app_state import AppState
from .view.main_window import MainWindow


def get_r_path(path):
    return str(Path(__file__).joinpath("../resources").resolve().joinpath(path))


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="sip")
    warnings.filterwarnings("ignore", message=".*sipPyTypeDict.*")
    warnings.filterwarnings("ignore", message=".*sipPyTypeDictRef.*")

    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("anirban.majumder.animedownloader")
    except (ImportError, AttributeError):
        pass

    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    QFontDatabase.addApplicationFont(get_r_path("Yellowtail.ttf"))

    splash = QSplashScreen(QPixmap(get_r_path("logo.png")))
    splash.show()
    app.processEvents()

    if not os.path.exists(data_dir):
        from .setup import setup
        setup(cfg)

    state = AppState.load(
        anime_repo=AnimeRepository(cfg.animeFile.value),
        torrent_repo=TorrentRepository(cfg.torrentFile.value),
    )
    coordinator = Coordinator(
        state,
        use_proxy=lambda: cfg.useProxy.value,
        tick_interval=lambda: cfg.checkEpisodeInterval.value,
        max_concurrent=cfg.maxConcurrentDownloads.value,
        compress_videos=lambda: cfg.compressVideos.value,
        compress_use_cuda=lambda: cfg.compressUseCuda.value,
    )
    main_window = MainWindow(coordinator)
    coordinator.start()

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        main_window.showMinimized()
    else:
        main_window.show()

    if cfg.firstTime.value:
        main_window.show_first_time()

    splash.finish(main_window)
    app.exec_()
