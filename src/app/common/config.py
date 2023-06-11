# coding:utf-8
from enum import Enum
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator,  EnumSerializer, FolderValidator,)


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
        "MainWindow", "MinimizeToTray", True, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)

    #quality and providers
    onlineMvQuality = OptionsConfigItem(
        "Online", "MvQuality", MvQuality.FULL_HD, OptionsValidator(MvQuality), EnumSerializer(MvQuality))

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", False, BoolValidator())

    animeFile = ConfigItem("Anime", "AnimeFile", "data//anime_file.json")
    proxyPath = ConfigItem("Anime", "ProxyPath", "data//proxy.json")
    testProxy = ConfigItem("Anime", "TestProxy", "data//test_proxy.json")
    pingUrl = ConfigItem("Anime", "PingUrl", "https://www.google.com")
    maxThread = ConfigItem("Anime", "MaxThread", 40)






cfg = Config()
qconfig.load('data//config.json', cfg)