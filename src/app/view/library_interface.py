# coding:utf-8
import json
from PyQt5.QtGui import QDesktopServices, QFont
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtWidgets import  QVBoxLayout, QHBoxLayout, QSizePolicy, QWidget, QFrame
from qfluentwidgets import FlowLayout, PushButton

from .base_interface import GalleryInterface, ImageLabel, ScrollArea

from ..common.style_sheet import StyleSheet
from ..common.utils import get_img


class LibraryInterface(GalleryInterface):
    """ Library interface """

    deleteSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        scroll_area = ScrollArea()
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vBoxLayout.addWidget(scroll_area)
        grid_widget = QFrame()
        self.grid_layout = FlowLayout(self, needAni=True)
        grid_widget.setLayout(self.grid_layout)
        scroll_area.setWidget(grid_widget)
        scroll_area.setWidgetResizable(True)

        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(2, 2, 0, 0)

        StyleSheet.LIBRARY_INTERFACE.apply(self)

        with open('data/anime_file.json', 'r') as f:
            self.anime_data = json.load(f)

        self.img_size = (164, 240)
        self.update_grid()

    def update_grid(self):
        """ Update the grid layout """

        while self.grid_layout.count():
            widget = self.grid_layout.takeAt(0)
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        if not self.anime_data:
            title_label = QLabel("Add Anime from Search to see here")
            title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #fff; font-style: italic;")
            title_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(title_label)

        for anime in self.anime_data:
            # Create a vertical layout for each grid cell
            cell_widget = QWidget()
            cell_layout = QVBoxLayout()
            cell_widget.setLayout(cell_layout)
            cell_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.grid_layout.addWidget(cell_widget)

            # Create a label for the image
            image_label = ImageLabel(anime)
            image_label.setFixedSize(self.img_size[0], self.img_size[1])
            image_label.setStyleSheet("background-color: transparent;")
            image_label.delete_signal.connect(self.on_delete_signal)
            cell_layout.addWidget(image_label, alignment=Qt.AlignCenter)
            # Load the image from the URL
            url = anime['img']
            self.load_img(url, image_label)

            # Create a label for the title
            name = anime['name'] if len(anime['name']) <= 28 else anime['name'][:28] + '...'
            title_label = QLabel(name)
            title_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #fff;")
            title_label.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(title_label)


            # Create a horizontal layout for the buttons
            button_layout = QHBoxLayout()
            cell_layout.addLayout(button_layout)

            # Create a button for watching online
            font = QFont()
            font.setPointSize(8)
            watch_online_button = PushButton('Watch Online')
            watch_online_button.setFont(font)
            watch_online_button.clicked.connect(lambda checked, url=anime['watch_url']: self.on_watch_online_button_clicked(url))
            button_layout.addWidget(watch_online_button)

            # Create a button for watching locally
            watch_local_button = PushButton('Watch Local')
            watch_local_button.setFont(font)
            watch_local_button.clicked.connect(lambda checked, path=anime['output_dir']: self.on_watch_local_button_clicked(path))
            button_layout.addWidget(watch_local_button)

    def load_img(self, url, label):
        pixmap = get_img(url)
        scaled_pixmap = pixmap.scaled(self.img_size[0], self.img_size[1])
        label.setPixmap(scaled_pixmap)

    def on_watch_online_button_clicked(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def on_watch_local_button_clicked(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def add_anime(self, anime):
        self.anime_data.insert(0, anime)
        self.update_grid()


    def on_delete_signal(self, id):
        self.anime_data = [anime for anime in self.anime_data if anime['id'] != id]
        self.update_grid()
        self.deleteSignal.emit(id)