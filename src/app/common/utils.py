from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, urlparse
import os, json
import socks, socket, requests
from bs4 import BeautifulSoup
from .constants import Constants as constants
from PyQt5.QtGui import QPixmap
from .config import cfg

download_path = cfg.downloadFolder.value
anime_file = cfg.animeFile.value
proxy = cfg.proxyPath.value
max_threads = cfg.maxThread.value
pingUrl = cfg.pingUrl.value



def compare_magnet_links(link1, link2):
    query1 = urlparse(link1).query
    query2 = urlparse(link2).query
    xt1 = parse_qs(query1).get('xt', [None])[0]
    xt2 = parse_qs(query2).get('xt', [None])[0]
    return xt1 == xt2


def get_nyaa_search_result(anime):
    proxies = read_proxies_from_file(proxy)
    results = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(get_nyaa_search_result_with_proxy, anime, proxy) for proxy in proxies]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.extend(result)
                break

    socks.set_default_proxy()
    socket.socket = socks.socksocket
    if results:
        return results
    return None


def get_nyaa_search_result_with_proxy(anime, proxy):
    torrent = []
    try:
        socks.set_default_proxy(socks.SOCKS4, proxy.split(':')[0], int(proxy.split(':')[1]))
        socket.socket = socks.socksocket
        url = f'https://nyaa.si/?q={anime}&s=seeders&o=desc'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        result = soup.find('table', {'class': 'torrent-list'}).find('tbody').find_all('tr')
        for r in result:
            title = r.find('a', {'href': lambda x: x.startswith('/view') and not x.endswith('#comments')})['title']
            magnet_link = r.find('a', {'href': lambda x: x.startswith('magnet')})['href']
            torrent.append([title, magnet_link])
        return torrent
    except requests.RequestException as e:
        return torrent


def read_proxies_from_file(proxy_path):
    with open(proxy_path, 'r') as f:
        return f.read().splitlines()



def remove_invalid_chars(path: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        path = path.replace(char, '')
    return path


def get_watch_url(title):
    url = f'https://9anime.pl/filter?keyword={title}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    result = soup.select_one('div.ani.items > div > div > div > a')
    watch_url = 'https://9anime.pl' + result['href']
    return watch_url


def get_anime_list(name):
    query = constants.list_query
    variables = {
        'search': name
    }
    url = constants.api_url
    response = requests.post(url, json={'query': query, 'variables': variables})
    data = json.loads(response.text)
    return data['data']['Page']['media']


def get_img(url):
    if not os.path.exists("cache"):
        os.makedirs("cache")
    url_split_last_part = url.split("/")[-1]
    try:
        pixmap = QPixmap(f"cache/{url_split_last_part}")
        if not pixmap.isNull():
            return pixmap
        response = requests.get(url)
        data = response.content
        pixmap = QPixmap()
        success = pixmap.loadFromData(data)
        if success:
            pixmap.save(f"cache/{url_split_last_part}")
            return pixmap
    except Exception as e:
        print(f"Error loading image: {e}")
    default_pixmap = QPixmap("resource/logo.png")
    return default_pixmap


def get_anime_detail(r):
    name = r["title"]["romaji"]
    season = r["season"]
    watch_url = get_watch_url(r["title"]["romaji"])
    airing = r["status"] == 'RELEASING'
    total_episodes = r["episodes"]
    #check if total episodes is null
    if not total_episodes:
        total_episodes = 24
    output_dir = os.path.join(download_path, remove_invalid_chars(name))
    #if not os.path.exists(output_dir):
    #    os.makedirs(output_dir)
    episodes_to_download = list(range(1, total_episodes + 1))
    info = {"name": name, "format": r["format"], "airing": airing,
            "total_episodes": total_episodes, "img": r["coverImage"]["extraLarge"],
            "output_dir": output_dir, "episodes_to_download": episodes_to_download,
            "watch_url": watch_url, "id": r["id"], "season": season}
    return info


def make_choice(list):
    start_index = 0
    end_index = min(len(list), 5)
    while True:
        for i in range(start_index, end_index):
            name = list[i][0]
            print(f"{i + 1}. {name}")
        print(f"{end_index + 1}. Show more")
        print(f"{end_index + 2}. None of the above")
        choice = input("Enter your choice: ")
        if not choice.isdigit():
            return
        choice = int(choice)
        if choice >= end_index + 2 or choice < 1:
            return
        elif choice == end_index + 1:
            start_index += 4
            end_index = min(len(list), end_index + 4)
        else:
            break
    return choice - 1
