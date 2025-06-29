"""
A simple and beautiful anime downloader and streamer.
"""
import os
import sys
import warnings

# Suppress SIP deprecation warnings
warnings.filterwarnings("ignore", message=".*sipPyTypeDict.*", category=DeprecationWarning)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap
from pathlib import Path
from .modules.common.config import cfg , data_dir
from .modules.view.main_window import MainWindow

def get_r_path(path):
    return str(Path(__file__).joinpath("../resources").resolve().joinpath(path))

def main():
    # Suppress various SIP and PyQt related warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="sip")
    warnings.filterwarnings("ignore", message=".*sipPyTypeDict.*")
    warnings.filterwarnings("ignore", message=".*sipPyTypeDictRef.*")

    try:
        # get custom app id for windows
        from ctypes import windll
        myappid = 'anirban.majumder.animedownloader'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except (ImportError, AttributeError):
        pass


    # enable dpi scale
    if cfg.get(cfg.dpiScale) == 'Auto':
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    else:
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
        os.environ['QT_SCALE_FACTOR'] = str(cfg.get(cfg.dpiScale))

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # create application
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    QFontDatabase.addApplicationFont(get_r_path('Yellowtail.ttf'))

    #show splash screen
    pixmap = QPixmap(get_r_path('logo.png'))
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()

    # run on first time setup
    if not os.path.exists(data_dir):
        from .setup import setup
        setup(cfg)

    # create main window
    main_window = MainWindow()

    # check for updates
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        main_window.showMinimized()
    else:
        main_window.show()

    # show first time intro
    if cfg.firstTime.value:
        main_window.showFirstTime()

    # close splash screen
    splash.finish(main_window)

    app.exec_()