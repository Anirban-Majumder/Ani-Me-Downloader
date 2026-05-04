# coding: utf-8
"""Confirm-anime form. Output read by SearchInterface."""
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFormLayout, QHBoxLayout, QLabel
from qfluentwidgets import ComboBox, LineEdit, SpinBox
from qfluentwidgets.components.dialog_box.dialog import MaskDialogBase, Ui_MessageBox

from ..view.image_cache import get_img


class AnimeDialog(MaskDialogBase, Ui_MessageBox):
    """Confirm-anime form. download_type ∈ {Full, Episodewise, None}."""

    def __init__(self, anime, parent=None):
        super().__init__(parent)
        title = "Verify and Confirm Info"
        content = (
            "Make sure this info is correct and make corrections as necessary "
            "and Make sure of season no.\nPLEASE REMOVE SEASON AND PART FROM THE TITLE \n"
            "eg. 'Attack on Titan Season 2' should be 'Attack on Titan' \n"
            "or  'Nanatsu no Taizai: Kamigami no Gekirin' should be 'Nanatsu no Taizai'"
        )
        self._setUpUi(title, content, self.widget)
        self.yesButton.setText("Confirm")

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)
        self.message_box_layout = QHBoxLayout()
        self.message_box_layout.setContentsMargins(24, 0, 24, 0)
        self.textLayout.setContentsMargins(24, 24, 24, 0)
        self.vBoxLayout.insertLayout(1, self.message_box_layout)

        img = anime["coverImage"]["extraLarge"]
        name = anime["title"]["romaji"]
        airing = anime["status"] in ("RELEASING", "HIATUS", "CANCELLED")
        season = anime["season"]
        total_ep = anime["episodes"] if anime["episodes"] else 13
        airing_ep = anime["nextAiringEpisode"]["episode"] if airing and anime["nextAiringEpisode"] else total_ep

        cover_image_label = QLabel()
        self.message_box_layout.addWidget(cover_image_label, Qt.AlignLeft)
        self.img_size = (164, 240)
        self.load_img(img, cover_image_label)

        form_layout = QFormLayout()
        self.message_box_layout.addLayout(form_layout, Qt.AlignRight)

        self.title_label = LineEdit(self)
        self.title_label.setText(name)
        self.title_label.setMinimumWidth(300)
        form_layout.addRow("Title:", self.title_label)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(8)

        self.season = SpinBox(self)
        self.season.setRange(1, 9999)
        self.season.setValue(season)
        form_layout.addRow("Season:", self.season)

        if airing:
            self.next_airing_episode = SpinBox(self)
            self.next_airing_episode.setRange(1, 9999)
            self.next_airing_episode.setEnabled(airing)
            self.next_airing_episode.setValue(airing_ep)
            form_layout.addRow("Next Airing Episode:", self.next_airing_episode)

        self.episodes = SpinBox(self)
        self.episodes.setRange(1, 9999)
        self.episodes.setValue(total_ep)
        form_layout.addRow("Total Episodes:", self.episodes)

        self.status_combobox = ComboBox(self)
        self.status_combobox.addItems(
            ["FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"]
        )
        self.status_combobox.setCurrentText(anime["status"])
        self.status_combobox.setEnabled(False)
        form_layout.addRow("Status:", self.status_combobox)

        self.download_type = ComboBox(self)
        self.download_type.addItems(["Full", "Episodewise", "None"])
        self.download_type.setCurrentText("Episodewise" if airing else "Full")
        form_layout.addRow("Download Type:", self.download_type)

        self.from_download = SpinBox(self)
        self.from_download.setRange(1, 9999)
        self.from_download.setValue(1)

        self.to_download = SpinBox(self)
        self.to_download.setRange(1, 9999)
        self.to_download.setValue(total_ep)

        self.from_download_label = QLabel("Download from episode:")
        self.to_download_label = QLabel("Download to episode:")

        form_layout.addRow(self.from_download_label, self.from_download)
        form_layout.addRow(self.to_download_label, self.to_download)

        self.update_widgets()
        self.download_type.currentTextChanged.connect(self.update_widgets)

    def load_img(self, url, label):
        pixmap = get_img(url)
        scaled = pixmap.scaled(self.img_size[0], self.img_size[1])
        label.setPixmap(scaled)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window() and e.type() == QEvent.Resize:
            self._adjustText()
        return super().eventFilter(obj, e)

    def update_widgets(self):
        if self.download_type.currentText() == "Episodewise":
            self.from_download.show()
            self.to_download.show()
            self.from_download_label.show()
            self.to_download_label.show()
        else:
            self.from_download.hide()
            self.to_download.hide()
            self.from_download_label.hide()
            self.to_download_label.hide()
