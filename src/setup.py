import os, getpass
from PyQt5.QtGui import QColor
from app.common.utils import check_network
from app.common.proxy_utils import *


def add_to_startup():
    file_path = os.path.realpath(__file__)
    USER_NAME = getpass.getuser()
    bat_path = r'C:\\Users\\%s\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup' % USER_NAME
    with open(bat_path + '\\' + "start_Anime_Downloader.bat", "w") as bat_file:
        bat_file.write(r'start "" "%s check"' % file_path)

def setup(cfg):
    if not check_network():
        print("Please check your network connection and try again.")
        exit()
    print("\nWorking on first time setup...")
    anime_file = os.path.join(os.path.dirname(__file__), "data", "anime_file.json")
    download_folder = os.path.join(os.path.dirname(__file__), "download")
    os.makedirs(download_folder, exist_ok=True)
    os.makedirs(os.path.dirname(anime_file), exist_ok=True)
    with open(anime_file, 'w') as f:
        f.write("[]")
    cfg.set(cfg.downloadFolder, download_folder)
    cfg.set(cfg.animeFile, anime_file)
    cfg.set(cfg.proxyPath, os.path.join(os.path.dirname(__file__), "data", "proxy.txt"))
    cfg.set(cfg.testProxy, os.path.join(os.path.dirname(__file__), "data", "test_proxy.txt"))
    cfg.set(cfg.themeColor, QColor('#ff0162'))
    cfg.save()
    add_to_startup()
    print("Added to startup successfully!")
    get_proxies()
    print("This will take a while, please wait...")
    check_proxies()
    print("First time setup completed successfully!\n")
