import os , shutil, getpass
from PyQt5.QtGui import QColor


def add_to_startup():
    file_path = os.path.realpath(__file__)
    if file_path.endswith(".py"):
        return
    elif os.name == "nt":
        user = getpass.getuser()
        startup_path = r'C:/Users/%s/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup' % user
        shortcut_path = r'C:/Users/%s/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Ani-Me-Downloader/Ani-Me Downloader.lnk' % user
        shutil.copy(shortcut_path, startup_path)
    elif os.name == "posix":
        startup_path = os.path.expanduser("~/.config/autostart/")
        startup_shortcut_path = os.path.join(startup_path, "Ani-Me Downloader.desktop")
        with open(startup_shortcut_path, 'w') as shortcut:
            shortcut.write('[Desktop Entry]\n')
            shortcut.write('Type=Application\n')
            shortcut.write('Exec={} {}\n'.format(file_path, "check"))
            shortcut.write('Hidden=false\n')
            shortcut.write('NoDisplay=false\n')
            shortcut.write('X-GNOME-Autostart-enabled=true\n')
            shortcut.write('Name=Ani-Me Downloader\n')
            shortcut.write('Comment=Ani-Me Downloader\n')
    else:
        print("OS not supported")
        return

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
    print("\nWorking on first time setup...")
    os.makedirs(os.path.dirname(cfg.animeFile.value), exist_ok=True)
    with open(cfg.animeFile.value, 'w') as f:
        f.write("[]")
    cfg.set(cfg.downloadFolder, get_download_dir())
    cfg.save()
    #add_to_startup()
    #print("Added to startup successfully!")