# coding:utf-8
import os
from enum import Enum
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator,  EnumSerializer, FolderValidator,)

data_dir = os.path.join(os.path.expanduser("~"), ".Ani-Me-Downloader")

class MvQuality(Enum):
    """ MV quality enumeration class """

    FULL_HD = "Full HD"
    HD = "HD"
    SD = "SD"
    LD = "LD"


class Config(QConfig):
    """ Config of application """

    downloadFolder = ConfigItem(
        "Folders", "Download", "/download", FolderValidator())

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

    animeFile = ConfigItem("Anime", "AnimeFile", os.path.join(data_dir, "anime_file.json"))
    proxyPath = ConfigItem("Anime", "ProxyPath", os.path.join(data_dir, "proxy.txt"))
    testProxy = ConfigItem("Anime", "TestProxy", os.path.join(data_dir, "test_proxy.txt"))
    pingUrl = ConfigItem("Anime", "PingUrl", "https://www.google.com")
    firstTime = ConfigItem("Anime","FirstTime", False)
    maxThread = ConfigItem("Anime", "MaxThread", 6)


cfg = Config()
qconfig.load(os.path.join(data_dir, "config.json"), cfg)