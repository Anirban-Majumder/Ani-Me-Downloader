# coding:utf-8
import os
from enum import Enum
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator,  EnumSerializer, FolderValidator, ColorConfigItem)

data_dir = os.path.join(os.path.expanduser("~"), ".Ani-Me-Downloader")

class MvQuality(Enum):
    """ MV quality enumeration class """

    FULL_HD = "Full HD"
    HD = "HD"
    SD = "SD"
    LD = "LD"


class Config(QConfig):
    """ Config of application """

    # folders
    downloadFolder = ConfigItem("Folders", "Download", "/download", FolderValidator())
    animeFile = ConfigItem("Folders", "AnimeFile", os.path.join(data_dir, "anime_file.json"))
    proxyPath = ConfigItem("Folders", "ProxyPath", os.path.join(data_dir, "proxy.txt"))
    testProxy = ConfigItem("Folders", "TestProxy", os.path.join(data_dir, "test_proxy.txt"))

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
    pingUrl = ConfigItem("Miscellaneous", "PingUrl", "https://example.com/")
    firstTime = ConfigItem("Miscellaneous", "FirstTime", True)
    maxThread = ConfigItem("Miscellaneous", "MaxThread", 6)

    # last run
    proxyLastChecked = ConfigItem("Lastrun", "ProxyLastChecked", 0)
    animeLastChecked = ConfigItem("Lastrun", "AnimeLastChecked", 0)

    # theme
    themeColor = ColorConfigItem("QFluentWidgets", "ThemeColor", '#29f1ff')


cfg = Config()
qconfig.load(os.path.join(data_dir, "config.json"), cfg)