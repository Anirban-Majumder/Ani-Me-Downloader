# coding: utf-8
"""Application config. qfluentwidgets.QConfig instance."""
import os
from enum import Enum

from qfluentwidgets import (
    BoolValidator,
    ColorConfigItem,
    ConfigItem,
    EnumSerializer,
    FolderValidator,
    OptionsConfigItem,
    OptionsValidator,
    QConfig,
    RangeConfigItem,
    RangeValidator,
    qconfig,
)

from .paths import data_dir, download_dir


class MvQuality(Enum):
    FULL_HD = "Full HD"
    HD = "HD"
    SD = "SD"
    LD = "LD"


class Config(QConfig):
    """Application config (persisted to ~/.Ani-Me-Downloader/config.json)."""

    downloadFolder = ConfigItem("Folders", "Download", download_dir, FolderValidator())
    checkEpisodeInterval = RangeConfigItem(
        "Download", "CheckEpisodeInterval", 3600, RangeValidator(60, 86400)
    )
    maxConcurrentDownloads = RangeConfigItem(
        "Download", "MaxConcurrentDownloads", 2, RangeValidator(1, 10)
    )

    animeFile = ConfigItem("Folders", "AnimeFile", os.path.join(data_dir, "anime_file.json"))
    torrentFile = ConfigItem("Folders", "TorrentFile", os.path.join(data_dir, "torrent_file.json"))

    minimizeToTray = ConfigItem("MainWindow", "MinimizeToTray", False, BoolValidator())
    showNotification = ConfigItem("MainWindow", "ShowNotification", True, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow",
        "DpiScale",
        "Auto",
        OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]),
        restart=True,
    )

    onlineMvQuality = OptionsConfigItem(
        "Online",
        "MvQuality",
        MvQuality.FULL_HD,
        OptionsValidator(MvQuality),
        EnumSerializer(MvQuality),
    )

    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", False, BoolValidator())

    compressVideos = ConfigItem("Compression", "CompressVideos", False, BoolValidator())
    compressUseCuda = ConfigItem("Compression", "CompressUseCuda", True, BoolValidator())

    useProxy = ConfigItem("Miscellaneous", "UseProxy", True, BoolValidator())
    pingUrl = ConfigItem("Miscellaneous", "PingUrl", "https://example.com/")
    firstTime = ConfigItem("Miscellaneous", "FirstTime", True)

    animeLastChecked = ConfigItem("Lastrun", "AnimeLastChecked", 0)

    themeColor = ColorConfigItem("QFluentWidgets", "ThemeColor", "#29f1ff")


cfg = Config()
qconfig.load(os.path.join(data_dir, "config.json"), cfg)
