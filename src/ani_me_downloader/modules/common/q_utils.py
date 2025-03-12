import requests
import re
import os
import subprocess

def find_qbittorrent_executable():
    common_dirs = [
        "C:\\Program Files\\qBittorrent",
        "C:\\Program Files (x86)\\qBittorrent",
    ]
    for directory in common_dirs:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.startswith("qbittorrent") and filename.endswith(".exe"):
                    return os.path.join(directory, filename)
    return None

def start_qbittorrent():
    qbittorrent_path = find_qbittorrent_executable()
    if qbittorrent_path:
        try:
            subprocess.Popen(qbittorrent_path)
            print("qBittorrent started successfully.")
        except Exception as e:
            print("Error:", e)
            return False
    else:
        print("qBittorrent executable not found.")
        return False
    return True


def get_qbittorrent_url():
    rss_url = "https://www.fosshub.com/feed/5b8793a7f9ee5a5c3e97a3b2.xml"
    headers = {"User-Agent": "qBittorrent/ ProgramUpdater (www.qbittorrent.org)"}
    response = requests.get(rss_url, headers=headers)

    latest_version = ""
    update_url = ""

    if response.status_code == 200:
        xml_data = response.text

        for match in re.finditer(r"<item>(.*?)</item>", xml_data, re.DOTALL):
            item_data = match.group(1)

            type_ = re.search(r"<type>(.*?)</type>", item_data)
            if type_ and type_.group(1) == 'Windows x64':
                version = re.search(r"<version>(.*?)</version>", item_data)
                update_link = re.search(r"<link>(.*?)</link>", item_data)

                if version and update_link:
                    latest_version = version.group(1)
                    update_url = update_link.group(1)
                    break
    else:
        print("Failed to fetch the updates RSS:", response.status_code)
 
    if os.name != "nt":
        update_url = update_url.split("?")[0]
    print("Latest version:", latest_version)
    print("Update URL:", update_url)
    return update_url
    