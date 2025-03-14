# coding: utf-8
from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig
from .utils import get_r_path


class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet  """

    SEARCH_INTERFACE = "search_interface"
    MAIN_WINDOW = "main_window"
    DOWNLOAD_INTERFACE = "download_interface"
    LIBRARY_INTERFACE = "library_interface"
    ICON_INTERFACE = "icon_interface"
    VIEW_INTERFACE = "view_interface"
    SETTING_INTERFACE = "setting_interface"
    BASE_INTERFACE = "base_interface"
    NAVIGATION_VIEW_INTERFACE = "navigation_view_interface"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        resource_path = f"qss/{theme.value.lower()}/{self.value}.qss"
        return get_r_path(resource_path)