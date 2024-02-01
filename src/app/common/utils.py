# coding:utf-8
from urllib.parse import parse_qs, urlparse
import os, time, re, requests
import requests
from bs4 import BeautifulSoup
from PyQt5.QtGui import QPixmap
from app.common.config import cfg, data_dir
from app.common.constants import Constants

anime_file = cfg.animeFile.value
pingUrl = cfg.pingUrl.value
useProxy = cfg.useProxy.value


def compare_magnet_links(link1, link2):
    query1 = urlparse(link1).query
    query2 = urlparse(link2).query
    xt1 = parse_qs(query1).get('xt', [None])[0]
    xt2 = parse_qs(query2).get('xt', [None])[0]
    return xt1 == xt2


def get_nyaa_search_result(name):
    torrent = []
    parms = {'f' : '0', 'c' : '1_0', 'q': name, 's': 'seeders', 'o': 'desc'}
    response = requests.get(Constants.proxy_url if useProxy else Constants.nyaa_url, parms)
    print("Request URL:", response.url)
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
            seed= r.find('td', {'class': 'text-center'}).find_next_sibling('td').find_next_sibling('td').find_next_sibling('td').text
            #print(seed, size, title)
            torrent.append([title, magnet_link, size])
    except Exception as e:
        print(f"Error parsing nyaa.si: {e}")

    print(f"Found {len(torrent)} torrents")
    return torrent


def remove_non_alphanum(string):
    pattern = re.compile(r'[^\w\s]|_', re.UNICODE)
    return pattern.sub('', string)


def clean_title(title):
    if re.search(r'season', title, re.IGNORECASE):
        title = re.split(r'season', title, flags=re.IGNORECASE)[0]
    if re.search(r'part', title, re.IGNORECASE):
        title = re.split(r'part', title, flags=re.IGNORECASE)[0]
    title = remove_non_alphanum(title)
    return title.strip()


def get_watch_url(title):
    url = f'{Constants.nineanime_url}/filter'
    params = {'keyword': title}
    response = requests.get(url, params=params, timeout=5)
    soup = BeautifulSoup(response.text, 'html.parser')
    url = soup.find('div', {'class': 'item'}).find('a')['href']
    watch_url = Constants.nineanime_url + url
    return watch_url


def get_anime_list(name):
    query = Constants.list_query
    variables = {
        'search': name
    }
    url = Constants.api_url
    response = requests.post(url, json={'query': query, 'variables': variables})
    data = response.json()
    return data['data']['Page']['media']


def get_img(url):
    cache_dir = os.path.join(data_dir, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    url_split_last_part = url.split("/")[-1]
    path = os.path.join(cache_dir, url_split_last_part)
    try:
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            return pixmap
        response = requests.get(url)
        data = response.content
        pixmap = QPixmap()
        success = pixmap.loadFromData(data)
        if success:
            pixmap.save(path)
            return pixmap
    except Exception as e:
        print(f"Error loading image: {e}")
    default_pixmap = QPixmap(os.path.join("app","resource","logo.png"))
    return default_pixmap


def get_season(url):
    response = requests.get(url, timeout=5)
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


def check_network(url = pingUrl):
    try:
        requests.get(url, timeout=5)
        return True
    except:
        return False