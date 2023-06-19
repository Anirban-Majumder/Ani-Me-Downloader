# coding:utf-8
import concurrent.futures
from threading import Event
from urllib.parse import parse_qs, urlparse
import os, json, random, time
import socks, socket, requests
from bs4 import BeautifulSoup
from .constants import Constants as constants
from PyQt5.QtGui import QPixmap
from .config import cfg

download_path = cfg.downloadFolder.value
anime_file = cfg.animeFile.value
proxy_file = cfg.proxyPath.value
max_threads = cfg.maxThread.value
pingUrl = cfg.pingUrl.value



def compare_magnet_links(link1, link2):
    query1 = urlparse(link1).query
    query2 = urlparse(link2).query
    xt1 = parse_qs(query1).get('xt', [None])[0]
    xt2 = parse_qs(query2).get('xt', [None])[0]
    return xt1 == xt2


def requests_get(url):
    print(url)
    stop_event = Event()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    with open(proxy_file, 'r') as f:
        proxies = f.read().splitlines()
    random.shuffle(proxies)
    def fetch(proxy):
        #print(stop_event.is_set())
        if not stop_event.is_set():
            try:
                socks.set_default_proxy(socks.SOCKS4, proxy.split(':')[0], int(proxy.split(':')[1]))
                socket.socket = socks.socksocket
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                if response.status_code == 200:
                    stop_event.set()
                    return response
            except:
                pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        results = executor.map(fetch, proxies)
        for result in results:
            if result:
                return result
    print("No result from the site")
    return None


def get_nyaa_search_result(name):
    torrent = []
    response = requests_get(f'https://nyaa.si/?q={name}&s=seeders&o=desc')
    socks.set_default_proxy()
    socket.socket = socks.socksocket
    if not response:
        return torrent
    soup = BeautifulSoup(response.text, 'html.parser')
    if "No results found" in soup.text:
        return torrent
    try:
        result = soup.find('table', {'class': 'torrent-list'}).find('tbody').find_all('tr')
        for r in result:
            title = r.find('a', {'href': lambda x: x.startswith('/view') and not x.endswith('#comments')})['title']
            magnet_link = r.find('a', {'href': lambda x: x.startswith('magnet')})['href']
            size= r.find('td', {'class': 'text-center'}).find_next_sibling('td').text
            seed= r.find('td', {'class': 'text-center'}).find_next_sibling('td').find_next_sibling('td').text
            print(seed, size, title)
            torrent.append([title, magnet_link, size])
    except Exception as e:
        print(f"Error parsing nyaa.si: {e}")
    return torrent


def remove_invalid_chars(path, replace_with=''):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        path = path.replace(char, replace_with)
    return path


def get_watch_url(title):
    url = f'https://9anime.pl/filter?keyword={title}'
    response = requests.get(url, timeout=5)
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
    name = remove_invalid_chars(r["title"]["romaji"])
    watch_url = get_watch_url(r["title"]["romaji"])
    season = get_season(watch_url)
    airing = r["status"] == 'RELEASING'
    total_episodes = 24 if not r["episodes"] else r["episodes"]
    output_dir = os.path.join(download_path, remove_invalid_chars(name))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    episodes_to_download = list(range(r["from"], r["to"]+ 1))
    info = {"name": name, "format": r["format"], "airing": airing,
            "total_episodes": total_episodes, "img": r["coverImage"]["extraLarge"],
            "output_dir": output_dir, "episodes_to_download": episodes_to_download,
            "watch_url": watch_url, "id": r["id"], "season": season}
    return info


def get_season(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup= BeautifulSoup(response.text, 'html.parser')
        try:
            season = soup.find('div', {'class': 'swiper-slide season active'}).find('div', {'class': 'name'}).text.strip()
            season = int(season.split(' ')[1])
        except Exception as e:
            season = 1
            print(e)
    return season


def get_time_diffrence(req_time):

    current_time = int(time.time())
    time_difference = req_time - current_time
    days = time_difference // (24 * 3600)
    time_difference = time_difference % (24 * 3600)
    hours = time_difference // 3600
    time_difference %= 3600
    minutes = time_difference // 60

    return days, hours, minutes


def check_network(url="https://google.com"):
    try:
        requests.get(url, timeout=5)
        return True
    except:
        return False