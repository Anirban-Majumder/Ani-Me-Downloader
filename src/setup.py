import os
from PyQt5.QtGui import QColor
from app.common.utils import check_network
from app.common.proxy_utils import get_proxies, check_proxies


def get_download_dir():
    if os.name == "nt":
        import winreg
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders")
        downloads_path = winreg.QueryValueEx(reg_key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
        winreg.CloseKey(reg_key)
        return downloads_path
    else:
        from pathlib import Path
        return str(os.path.join(Path.home(), "Downloads"))

def setup(cfg):
    if not check_network():
        print("Please check your network connection and try again.")
        exit()
    print("\nWorking on first time setup...")
    os.makedirs(os.path.dirname(cfg.animeFile.value), exist_ok=True)
    with open(cfg.animeFile.value, 'w') as f:
        f.write("[]")
    cfg.set(cfg.downloadFolder, get_download_dir())
    cfg.set(cfg.themeColor, QColor('#ff0162'))
    cfg.save()
    print("Added to startup successfully!")
    get_proxies()
    print("This will take a while, please wait...")
    check_proxies()
    print("First time setup completed successfully!\n")
