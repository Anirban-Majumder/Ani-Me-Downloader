import os
from PyQt5.QtGui import QColor
from app.common.utils import check_network
from app.common.proxy_utils import *

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
    get_proxies()
    print("This will take a while, please wait...")
    check_proxies()
    print("First time setup completed successfully!\n")





import subprocess

def create_scheduled_task(task_name, script_path, trigger_time, arguments,username):
    command = f'schtasks /create /tn "{task_name}" /tr "{script_path} {arguments}" /sc onlogon /ru {username}'
    subprocess.run(command, shell=True)


task_name = 'aaaTask'
script_path = r'C:\\Users\\Anirban\\Desktop\\run.bat'
trigger_time = '07:00'
arguments = 'check'
username = os.getlogin()

#create_scheduled_task(task_name, script_path, trigger_time, arguments,username)