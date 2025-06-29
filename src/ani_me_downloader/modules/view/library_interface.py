# coding:utf-8
from PyQt5.QtCore import Qt, QRect, QRectF, QUrl, pyqtSignal
from PyQt5.QtGui import  QPainter, QColor, QPainterPath,  QDesktopServices
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
                             QWidget, QVBoxLayout, QLabel, QWidget, QFrame)

from qfluentwidgets import (FluentIcon, FlowLayout, PushButton,PrimaryToolButton)

from .base_interface import BaseInterface, ScrollArea
from ..common.style_sheet import StyleSheet
from ..common.utils import get_img, get_time_diffrence
from ..common.config import cfg
from ..common.mal import update_anime_status

class ImageLabel(QLabel):
    delete_signal = pyqtSignal(int)
    anime_sync_signal = pyqtSignal(int)

    def __init__(self, anime, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anime = anime
        self.setMouseTracking(True)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the image with rounded corners
        rect = QRect(0, 0, self.width(), self.height())
        path = QPainterPath()
        corner_radius = 20
        rectF = QRectF(rect)
        path.addRoundedRect(rectF, corner_radius, corner_radius)
        painter.setClipPath(path)
        if self.pixmap():
            painter.drawPixmap(rect, self.pixmap())



        # Draw a black rectangle at the bottom of the image
        bottom_rect_height = int(self.height() * 0.07)
        bottom_rect = QRect(0, self.height() - bottom_rect_height, self.width(), bottom_rect_height + 1)
        painter.fillRect(bottom_rect, QColor('black'))

        # Set the font and pen for drawing text
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.setPen(QColor('white'))

        # Draw the current airing episode (if anime is airing)
        if self.anime.airing:
            current_episode_text = f"A{self.anime.last_aired_episode}"
            current_episode_rect = QRect(10, self.height() - bottom_rect_height, 25, bottom_rect_height)
            fill_rect=QRect(0, self.height() - bottom_rect_height, 35, bottom_rect_height)
            painter.fillRect(fill_rect, QColor('green'))
            painter.drawText(current_episode_rect, Qt.AlignCenter, current_episode_text)

        # Draw the number of downloaded episodes
        if self.anime.episodes_downloaded and self.anime.episodes_downloaded[0] == "full":
            ep_dn = self.anime.total_episodes
        else:
            ep_dn = len(self.anime.episodes_downloaded)
        downloaded_episodes_text = f"D{ep_dn}"
        downloaded_episodes_rect = QRect(self.width()-58, self.height() - bottom_rect_height , 25, bottom_rect_height)
        painter.fillRect(downloaded_episodes_rect, QColor('blue'))
        painter.drawText(downloaded_episodes_rect, Qt.AlignCenter, downloaded_episodes_text)

        # Draw the total number of episodes
        total_episodes_text = f"T{self.anime.total_episodes}"
        total_episodes_rect = QRect(self.width()-33, self.height() - bottom_rect_height , 25, bottom_rect_height)
        total_fill = QRect(self.width()-33, self.height() - bottom_rect_height , 33, bottom_rect_height)
        painter.fillRect(total_fill, QColor('grey'))
        painter.drawText(total_episodes_rect, Qt.AlignCenter, total_episodes_text)

    def enterEvent(self, event):
            # Create a horizontal layout for the buttons
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(5)
            
            # Add sync button to the left
            sync_button = PrimaryToolButton(FluentIcon.SYNC)
            sync_button.clicked.connect(self.on_sync_button_clicked)
            button_layout.addWidget(sync_button)
            
            # Add spacer to push delete button to the right
            button_layout.addStretch()
            
            # Add delete button to the right
            delete_button = PrimaryToolButton(FluentIcon.DELETE)
            delete_button.clicked.connect(self.on_delete_button_clicked)
            button_layout.addWidget(delete_button)
            
            # Add the button layout to the main layout
            self.layout.addLayout(button_layout, 0)
    
            if self.anime.airing:
                days, hours, minutes = get_time_diffrence(self.anime.next_eta)
                next_air= QLabel(f"Next Airing: {self.anime.last_aired_episode+1}")
                time_left = QLabel(f"Time Left: {days} days {hours} hrs" if days else f"Time Left: {hours} hrs {minutes} mins")
            else:
                if len(self.anime.episodes_downloaded) == self.anime.total_episodes or (self.anime.episodes_downloaded and self.anime.episodes_downloaded[0] == "full"):
                    status = QLabel("Completely Downloaded")
                else:
                    status = QLabel(f"{len(self.anime.episodes_downloaded)} out of {self.anime.total_episodes} episodes done")
    
            if self.anime.episodes_downloaded and self.anime.episodes_downloaded[0] == "full":
                ep_dn = self.anime.total_episodes
            else:
                ep_dn = len(self.anime.episodes_downloaded)
            ep_downloaded = QLabel(f"Downloaded: {ep_dn}")
            total_ep = QLabel(f"Episodes: {self.anime.total_episodes}")
    
            labels=[next_air,time_left,ep_downloaded,total_ep] if self.anime.airing else [ep_downloaded,total_ep, status]
            for label in labels:
                label.setMinimumHeight(30)
                label.setMaximumHeight(30)
                label.setObjectName("animeInfo")
                self.layout.addWidget(label, alignment=Qt.AlignTop)
    
            self.setStyleSheet(f"background-color: rgba({cfg.themeColor.value.red()}, {cfg.themeColor.value.green()}, {cfg.themeColor.value.blue()}, 210);")
    
    def leaveEvent(self, event):
            self.setStyleSheet("background-color: transparent;")
    
            # Remove all labels
            labels = self.findChildren(QLabel)
            for label in labels:
                label.deleteLater()
    
            # Remove all buttons
            buttons = self.findChildren(PrimaryToolButton)
            for button in buttons:
                button.deleteLater()
                
            # Clean up any layouts that were added
            for i in reversed(range(self.layout.count())):
                item = self.layout.itemAt(i)
                if isinstance(item, QHBoxLayout):
                    # Remove all widgets from the layout
                    while item.count():
                        widget = item.takeAt(0)
                        if widget.widget():
                            widget.widget().deleteLater()
                    # Remove the layout itself
                    self.layout.removeItem(item)
        

    def on_delete_button_clicked(self):
        self.delete_signal.emit(self.anime.id)

    def on_sync_button_clicked(self):
        self.anime_sync_signal.emit(self.anime.idMal)


class LibraryInterface(BaseInterface):
    """ Library interface """

    deleteSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        scroll_area = ScrollArea()
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vBoxLayout.addWidget(scroll_area)
        grid_widget = QFrame()
        self.grid_layout = FlowLayout(self, needAni=True)
        self.grid_layout._verticalSpacing = 0
        self.grid_layout._horizontalSpacing = 0
        grid_widget.setLayout(self.grid_layout)
        scroll_area.setWidget(grid_widget)
        scroll_area.setWidgetResizable(True)

        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(2, 2, 0, 0)

        StyleSheet.LIBRARY_INTERFACE.apply(self)
        self.part=parent
        self.animes = self.parent().animes
        self.delete_lable = False

        if not self.animes:
            self.delete_lable = True
            self.title_label = QLabel("Add Anime from Search to see here")
            self.title_label.setObjectName("title")
            self.vBoxLayout.addWidget(self.title_label, Qt.AlignCenter)

        self.img_size = (164, 240)
        self.update_grid(self.animes)

    def update_grid(self, animes):
        """ Update the grid layout """
        self.animes = animes

        if self.delete_lable and self.animes:
            self.title_label.setParent(None)
            self.title_label.deleteLater()
            self.delete_lable = False

        while self.grid_layout.count():
            widget = self.grid_layout.takeAt(0)
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        for anime in self.animes:
            # Create a vertical layout for each grid cell
            cell_widget = QWidget()
            cell_layout = QVBoxLayout()
            cell_widget.setLayout(cell_layout)
            cell_widget.setObjectName('animeBox')
            self.grid_layout.addWidget(cell_widget)

            # Create a label for the image
            image_label = ImageLabel(anime)
            image_label.setFixedSize(self.img_size[0], self.img_size[1])
            image_label.setStyleSheet("background-color: transparent;")
            image_label.delete_signal.connect(self.on_delete_signal)
            image_label.anime_sync_signal.connect(self.on_sync_button_clicked)
            cell_layout.addWidget(image_label, alignment=Qt.AlignCenter)
            # Load the image from the URL
            url = anime.img
            self.load_img(url, image_label)

            # Create a label for the title
            name = anime.name if len(anime.name) <= 44 else anime.name[:44] + '...'

            title_label = QLabel(name)
            title_label.setObjectName('animeTitle')
            title_label.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(title_label)


            # Create a horizontal layout for the buttons
            button_layout = QHBoxLayout()
            cell_layout.addLayout(button_layout)

            # Create a button for watching online
            watch_online_button = PushButton('Watch Online')
            watch_online_button.setObjectName('button')
            watch_online_button.clicked.connect(self.on_watch_online_button_clicked(anime.watch_url))
            button_layout.addWidget(watch_online_button)

            # Create a button for watching locally
            watch_local_button = PushButton('Watch Local')
            watch_local_button.setObjectName('button')
            watch_local_button.clicked.connect(self.on_watch_local_button_clicked(anime.output_dir))
            button_layout.addWidget(watch_local_button)

    def load_img(self, url, label):
        pixmap = get_img(url)
        scaled_pixmap = pixmap.scaled(self.img_size[0], self.img_size[1])
        label.setPixmap(scaled_pixmap)

    def on_watch_online_button_clicked(self, url):
        return lambda: QDesktopServices.openUrl(QUrl(url))

    def on_watch_local_button_clicked(self, path):
        return lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def on_sync_button_clicked(self, id):
        from ..components.customdialog import SyncDialog

        # Find the anime with the given MAL ID
        anime_data = None
        for anime in self.animes:
            if anime.idMal == id:
                anime_data = anime
                break

        if anime_data:
            dialog = SyncDialog(anime_data, self)
            if dialog.exec_():
                # User clicked Update
                form_data = dialog.get_form_data()
                try:
                    update_anime_status(**form_data)
                    self.part.showSuccess("Anime status updated successfully")
                except Exception as e:
                    print(f"Error updating anime status: {e}")


    def on_delete_signal(self, id):
        from qfluentwidgets import MessageBox
        for anime in self.animes:
            if anime.id == id:
                anime_data = anime
                break

        title = "Confirm Delete"
        content = f"Are you sure you want to delete {anime_data.name} from your library? This will also delete all downloaded files."
        message = MessageBox(title, content, parent=self)
        if message.exec_():
            self.deleteSignal.emit(id)