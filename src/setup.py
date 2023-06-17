import os
from app.common.config import cfg
from app.common.proxy_utils import *

def setup():
    try:
        res=requests.get("https://www.google.com")
        res.raise_for_status()
    except Exception as e:
        print("\nFirst time setup failed! Please check your network connection and try again.")
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
    cfg.save()
    get_proxies()
    print("This will take a while, please wait...")
    check_proxies()
    print("First time setup completed successfully!\n")