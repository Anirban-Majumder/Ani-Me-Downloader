# coding:utf-8
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QApplication

from app.common.config import cfg , data_dir
from app.view.main_window import MainWindow

#get custom app id
try:
    from ctypes import windll
    myappid = 'anirban.majumder.animedownloader'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


# run on first time setup
if not os.path.exists(data_dir):
    from setup import setup
    setup(cfg)

# enable dpi scale
if cfg.get(cfg.dpiScale) == "Auto":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
else:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# create application
app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

# load fonts
QFontDatabase.addApplicationFont("app/resource/Yellowtail.ttf")


# create main window
w = MainWindow()

# check if the argument is 'check'
if len(sys.argv) > 1 and sys.argv[1] == 'check':
    # start the app minimized
    w.showMinimized()
else:
    # start the app normally
    w.show()

if cfg.firstTime.value:
    w.showFirstTime()

app.exec_()