# coding:utf-8
from qfluentwidgets import (SettingCardGroup, SwitchSettingCard,
                            OptionsSettingCard, PushSettingCard, ScrollArea,
                            ExpandLayout, CustomColorSettingCard, setTheme, setThemeColor)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBar, RangeSettingCard
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog

from ..common.config import cfg
from ..common.style_sheet import StyleSheet


class SettingInterface(ScrollArea):
    """ Setting interface """

    checkUpdateSig = pyqtSignal()
    downloadFolderChanged = pyqtSignal(str)
    minimizeToTrayChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel("Settings", self)

        # download
        self.downloadGroup = SettingCardGroup(
            "On this PC", self.scrollWidget)
        self.downloadFolderCard = PushSettingCard(
            self.tr('Choose folder'),
            FIF.DOWNLOAD,
            "Download directory",
            cfg.get(cfg.downloadFolder),
            self.downloadGroup
        )
        self.downloadLimitCard = RangeSettingCard(
            cfg.maxConcurrentDownloads,
            FIF.DOWNLOAD,
            "Max concurrent downloads",
            "Maximum number of items to download at once",
            self.downloadGroup
        )
        self.checkEpisodeIntervalCard = RangeSettingCard(
            cfg.checkEpisodeInterval,
            FIF.UPDATE,
            "Check for new episodes (sec)",
            "How frequently to check for new episodes (in seconds)",
            self.downloadGroup
        )
        

        
        self.qualityandprovider = SettingCardGroup(self.tr('Quality & Providers'), self.scrollWidget)
        self.useProxyCard = SwitchSettingCard(
            FIF.VPN,
            self.tr('Use proxy'),
            self.tr('We recommend you to use proxy , '),
            configItem=cfg.useProxy,
            parent=self.qualityandprovider
        )
        self.onlineMvQualityCard = OptionsSettingCard(
            cfg.onlineMvQuality,
            FIF.VIDEO,
            self.tr('Anime quality'),
            texts=[
                self.tr('Full HD'), self.tr('HD'),
                self.tr('SD'), self.tr('LD')
            ],
            parent=self.qualityandprovider
        )
        # personalization
        self.personalGroup = SettingCardGroup(
            self.tr('Personalization'), self.scrollWidget)
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr('Application theme'),
            "Change the appearance of your application",
            texts=[
                self.tr('Light'), self.tr('Dark'),
                self.tr('Use system setting')
            ],
            parent=self.personalGroup
        )
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            self.personalGroup
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            "Interface zoom",
            "Change the size of widgets and fonts",
            texts=[
                "100%", "125%", "150%", "175%", "200%",
                "Use system setting"
            ],
            parent=self.personalGroup
        )
        # main panel
        self.mainPanelGroup = SettingCardGroup(self.tr('Main Panel'), self.scrollWidget)
        self.minimizeToTrayCard = SwitchSettingCard(
            FIF.MINIMIZE,
            self.tr('Minimize to tray after closing'),
            self.tr('Ani-Me-Downloader will continue to run in the background'),
            configItem=cfg.minimizeToTray,
            parent=self.mainPanelGroup
        )
        self.showNotificationCard = SwitchSettingCard(
            FIF.MESSAGE,
            self.tr('Show notification'),
            self.tr('Ani-Me-Downloader will show a notifications about things...'),
            configItem=cfg.showNotification,
            parent=self.mainPanelGroup
        )
        # update software
        self.updateSoftwareGroup = SettingCardGroup(
            "Software update", self.scrollWidget)
        self.updateOnStartUpCard = SwitchSettingCard(
            FIF.UPDATE,
            self.tr('Check for updates when the application starts'),
            self.tr('The new version will be more stable and have more features'),
            configItem=cfg.checkUpdateAtStartUp,
            parent=self.updateSoftwareGroup
        )
        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')
        StyleSheet.SETTING_INTERFACE.apply(self)

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(36, 30)

        # add cards to group
        
        self.downloadGroup.addSettingCard(self.downloadFolderCard)
        self.downloadGroup.addSettingCard(self.downloadLimitCard)
        self.downloadGroup.addSettingCard(self.checkEpisodeIntervalCard)
        self.qualityandprovider.addSettingCard(self.useProxyCard)
        self.qualityandprovider.addSettingCard(self.onlineMvQualityCard)
        self.mainPanelGroup.addSettingCard(self.minimizeToTrayCard)
        self.mainPanelGroup.addSettingCard(self.showNotificationCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)
        self.updateSoftwareGroup.addSettingCard(self.updateOnStartUpCard)


        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.downloadGroup)
        self.expandLayout.addWidget(self.qualityandprovider)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.mainPanelGroup)
        self.expandLayout.addWidget(self.updateSoftwareGroup)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.success(
            self.tr('Updated successfully'),
            self.tr('Configuration takes effect after restart'),
            duration=1500,
            parent=self
        )

    def __onDownloadFolderCardClicked(self):
        """ download folder card clicked slot """
        folder = QFileDialog.getExistingDirectory(
            self, "Choose folder", "./")
        if not folder or cfg.get(cfg.downloadFolder) == folder:
            return

        cfg.set(cfg.downloadFolder, folder)
        cfg.save()
        self.downloadFolderCard.setContent(folder)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        cfg.themeChanged.connect(setTheme)

        # download folder
        self.downloadFolderCard.clicked.connect(
            self.__onDownloadFolderCardClicked)

        # personalization
        self.themeColorCard.colorChanged.connect(setThemeColor)

