# coding:utf-8
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication

from app.common.config import cfg
from app.view.main_window import MainWindow


# run on first time setup
if not os.path.exists(os.path.join(os.path.dirname(__file__), "data")):
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
#QFontDatabase.addApplicationFont("app/resource/Aldrich.ttf")
#font = QFont("Aldrich")
#app.setFont(font)

# create main window
w = MainWindow()
w.show()

app.exec_()