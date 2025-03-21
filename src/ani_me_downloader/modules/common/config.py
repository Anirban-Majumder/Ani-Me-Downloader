# coding:utf-8
import os
from enum import Enum
from qfluentwidgets import (qconfig, QConfig, ConfigItem, RangeConfigItem,
                            OptionsConfigItem, BoolValidator, RangeValidator,
                            OptionsValidator,  EnumSerializer, FolderValidator, ColorConfigItem)

data_dir = os.path.join(os.path.expanduser("~"), ".Ani-Me-Downloader")
download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

class MvQuality(Enum):
    """ MV quality enumeration class """

    FULL_HD = "Full HD"
    HD = "HD"
    SD = "SD"
    LD = "LD"


class Config(QConfig):
    """ Config of application """

    # folders
    downloadFolder = ConfigItem("Folders", "Download", download_dir, FolderValidator())
    checkEpisodeInterval = RangeConfigItem(
        "Download", "CheckEpisodeInterval", 3600, RangeValidator(60, 86400)
    )  # Default 1 hour (3600 sec), min 1 min, max 24 hours
    
    maxConcurrentDownloads = RangeConfigItem(
        "Download", "MaxConcurrentDownloads", 2, RangeValidator(1, 10)
    )
    
    animeFile = ConfigItem("Folders", "AnimeFile", os.path.join(data_dir, "anime_file.json"))
    torrentFile = ConfigItem("Folders", "TorrentFile", os.path.join(data_dir, "torrent_file.json"))
    # main window
    minimizeToTray = ConfigItem(
        "MainWindow", "MinimizeToTray", False, BoolValidator())
    showNotification = ConfigItem(
        "MainWindow", "ShowNotification", True, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)

    #quality and providers
    onlineMvQuality = OptionsConfigItem(
        "Online", "MvQuality", MvQuality.FULL_HD, OptionsValidator(MvQuality), EnumSerializer(MvQuality))

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", False, BoolValidator())

    # miscellaneous
    useProxy = ConfigItem("Miscellaneous", "UseProxy", True, BoolValidator())
    pingUrl = ConfigItem("Miscellaneous", "PingUrl", "https://example.com/")
    firstTime = ConfigItem("Miscellaneous", "FirstTime", True)

    # last run
    animeLastChecked = ConfigItem("Lastrun", "AnimeLastChecked", 0)

    # theme
    themeColor = ColorConfigItem("QFluentWidgets", "ThemeColor", '#29f1ff')


cfg = Config()
qconfig.load(os.path.join(data_dir, "config.json"), cfg)