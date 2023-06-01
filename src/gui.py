#from main import *
import sys
import json
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QSizePolicy, QLabel, QScrollArea

class WorkerThread(QThread):
    update_text = pyqtSignal(str)

    def __init__(self, anime_name):
        QThread.__init__(self)
        self.anime_name = anime_name

    def run(self):
        pass
        #animes = load_animes(Anime,'animes.json')
        #new_anime=add_anime(self.anime_name)
        #animes.append(new_anime)
        #save_animes(animes, 'animes.json')



class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        # Set up the user interface
        self.setGeometry(100, 100, 700, 600)
        self.setWindowTitle('Anime Downloader')

        # Create a central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Add a vertical spacer
        layout.addStretch()

        # Create a horizontal layout for the search field and button
        search_layout = QHBoxLayout()
        layout.addLayout(search_layout)

        # Add a horizontal spacer
        search_layout.addStretch()

        # Create a text field for entering the anime name
        self.search_field = QLineEdit(self)
        self.search_field.setPlaceholderText('Enter anime name')
        self.search_field.resize(200, 30)
        search_layout.addWidget(self.search_field)

        # Create a button for starting the search
        self.search_button = QPushButton('Enter Anime', self)
        search_layout.addWidget(self.search_button)
        self.search_button.clicked.connect(self.on_search_button_clicked)

        # Add another horizontal spacer
        search_layout.addStretch()

        # Add another vertical spacer
        layout.addStretch()

        # Create a scroll area for the grid
        scroll_area = QScrollArea()
        # Set the size policy of the scroll area
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set the minimum height of the scroll area to 15% of the window height
        scroll_area.setMinimumHeight(int(self.height() * 0.85))

        layout.addWidget(scroll_area)

        # Create a widget for the grid
        grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        grid_widget.setLayout(self.grid_layout)
        scroll_area.setWidget(grid_widget)
        scroll_area.setWidgetResizable(True)

        # Create a network access manager for loading images
        self.nam = QNetworkAccessManager()

        # Load the anime data from a JSON file
        with open('data//anime_file.json', 'r') as f:
            anime_data = json.load(f)

        # Display the anime data in a grid
        row = 0
        col = 0
        for anime in anime_data:
            # Create a vertical layout for each grid cell
            cell_widget = QWidget()
            cell_layout = QVBoxLayout()
            cell_widget.setLayout(cell_layout)
            cell_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            cell_widget.setMinimumSize(220, 300)
            cell_widget.setMaximumSize(220, 300)
            self.grid_layout.addWidget(cell_widget, row, col)



            # Create a label for the title
            name = anime['name'] if len(anime['name']) <= 30 else anime['name'][:30] + '...'
            title_label = QLabel(name)
            title_label.setWordWrap(True)
            title_label.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(title_label)

            # Create a label for the image
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(image_label)

            # Load the image from the URL
            url = QUrl(anime['img'])
            request = QNetworkRequest(url)
            reply = self.nam.get(request)
            reply.finished.connect(lambda r=reply, l=image_label: self.on_image_loaded(r, l))

            # Create a button for watching online
            watch_online_button = QPushButton('Watch Online')
            watch_online_button.clicked.connect(lambda checked, url=anime['watch_url']: self.on_watch_online_button_clicked(url))
            cell_layout.addWidget(watch_online_button)

            # Create a button for watching locally
            watch_local_button = QPushButton('Watch Local')
            watch_local_button.clicked.connect(lambda checked, path=anime['output_dir']: self.on_watch_local_button_clicked(path))
            cell_layout.addWidget(watch_local_button)

            # Move to the next grid cell
            col += 1
            if col == 3:
                col = 0
                row += 1

    def on_search_button_clicked(self):
        # Start a worker thread to search for the anime
        anime_name = self.search_field.text()
        self.worker_thread = WorkerThread(anime_name)
        self.worker_thread.update_text.connect(self.update_text)
        self.worker_thread.start()

    def on_image_loaded(self, reply, label):
        data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        scaled_pixmap = pixmap.scaled(154, 220)
        label.setPixmap(scaled_pixmap)

    def on_watch_online_button_clicked(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def on_watch_local_button_clicked(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
