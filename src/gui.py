#from main import *
from utils import get_anime_list
import sys
import json
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices, QImage
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QSizePolicy, QLabel, QScrollArea, QDialog, QListWidget, QDialogButtonBox,QListWidgetItem, QFormLayout,QSpinBox,QComboBox


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

        # Create a dialog box
        dialog = QDialog(self)
        dialog.setWindowTitle('Search Results')
        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)

        # Create a label to display the search status
        search_status_label = QLabel('Searching...')
        dialog_layout.addWidget(search_status_label)
        anime_list = get_anime_list(anime_name)
        search_status_label.setText('Choose from the following results:')

        # Create a list widget to display the search results
        list_widget = QListWidget()
        for anime in anime_list[:10]:
            item = QListWidgetItem(anime['title']['romaji'])
            item.setData(Qt.UserRole, anime)
            list_widget.addItem(item)
        dialog_layout.addWidget(list_widget)

        # Create a button box with Accept, Cancel, and Show More buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        show_more_button = button_box.addButton('Show More', QDialogButtonBox.ActionRole)
        dialog_layout.addWidget(button_box)

        # Connect the button signals
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        show_more_button.clicked.connect(lambda: self.show_more_results(list_widget, anime_list))

        # Show the dialog box
        result = dialog.exec_()

        # Check the result
        if result == QDialog.Accepted:
            selected_anime = list_widget.currentItem().data(Qt.UserRole)
            self.show_anime_info(selected_anime)

    def show_more_results(self, list_widget, anime_list):
        current_count = list_widget.count()
        for anime in anime_list[current_count:current_count+10]:
            item = QListWidgetItem(anime['title']['romaji'])
            item.setData(Qt.UserRole, anime)
            list_widget.addItem(item)

    def show_anime_info(self, anime):
        # Create a dialog box
        anime_info_dialog = QDialog(self)
        anime_info_dialog.setWindowTitle(anime['title']['romaji'])
        dialog_layout = QHBoxLayout()
        anime_info_dialog.setLayout(dialog_layout)

        # Show the cover image on the left side of the dialog
        cover_image_label = QLabel()
        dialog_layout.addWidget(cover_image_label)

        # Load the cover image using a QNetworkAccessManager
        url = QUrl(anime['coverImage']['extraLarge'])
        request = QNetworkRequest(url)
        reply = self.nam.get(request)
        reply.finished.connect(lambda: self.on_image_loaded(reply, cover_image_label))

        # Create a form layout for the anime info on the right side of the dialog
        form_layout = QFormLayout()
        dialog_layout.addLayout(form_layout)

        # Add the anime title (not editable)
        title_label = QLabel(anime['title']['romaji'])
        form_layout.addRow('Title:', title_label)

        # Add a spin box for the next airing episode (only enabled if status is RELEASING)
        next_airing_episode_spinbox = QSpinBox()
        next_airing_episode_spinbox.setEnabled(anime['status'] == 'RELEASING')
        if anime["status"] == 'RELEASING':
            next_airing_episode_spinbox.setValue(anime['nextAiringEpisode']['episode'])
            form_layout.addRow('Next Airing Episode:', next_airing_episode_spinbox)

        # Add a spin box for the number of episodes
        episodes_spinbox = QSpinBox()
        episodes_spinbox.setValue(anime['episodes'])
        form_layout.addRow('Total Episodes:', episodes_spinbox)

        # Add a combo box for the status
        status_combobox = QComboBox()
        status_combobox.addItems(['FINISHED', 'RELEASING', 'NOT_YET_RELEASED'])
        status_combobox.setCurrentText(anime['status'])
        form_layout.addRow('Status:', status_combobox)

        # Add a spin box for the season
        season_spinbox = QSpinBox()
        season_spinbox.setValue(1)
        form_layout.addRow('Season:', season_spinbox)

        # Connect the status combo box signal to enable/disable the next airing episode spin box
        status_combobox.currentTextChanged.connect(lambda text: next_airing_episode_spinbox.setEnabled(text == 'RELEASING'))

        # Create a button box with Ok and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form_layout.addRow(button_box)

        # Connect the button signals
        button_box.accepted.connect(anime_info_dialog.accept)
        button_box.rejected.connect(anime_info_dialog.reject)

        # Show the dialog box
        result = anime_info_dialog.exec_()

        # Check the result
        if result == QDialog.Accepted:
            # Update the anime info with the edited values
            anime['episodes'] = episodes_spinbox.value()
            anime['status'] = status_combobox.currentText()
            anime['season'] = season_spinbox.value()
            if next_airing_episode_spinbox.isEnabled():
                anime['nextAiringEpisode'] = next_airing_episode_spinbox.value()
            else:
                anime['nextAiringEpisode'] = None
            #### TODO: add checks for the info  and episodes and test
            print(anime)


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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
