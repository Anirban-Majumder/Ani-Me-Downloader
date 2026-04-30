# coding:utf-8
from urllib.parse import parse_qs, urlparse
import os, time, re, requests
from bs4 import BeautifulSoup
from PyQt5.QtGui import QPixmap
from .config import cfg, data_dir
from .constants import Constants

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
    """Scrape Nyaa torrent rows.

    Returns a list of ``[title, magnet, size, seeds]`` where ``seeds`` is an
    int. Rows whose seed cell is missing or non-numeric default to 0.
    """
    torrents = []
    params = {'f': '0', 'c': '1_0', 'q': name, 's': 'seeders', 'o': 'desc'}
    try:
        response = requests.get(
            Constants.proxy_url if useProxy else Constants.nyaa_url,
            params,
            timeout=10,
        )
        print("Request URL:", response.url)
        if not response:
            return torrents
        soup = BeautifulSoup(response.text, 'html.parser')
        if "No results found" in soup.text:
            return torrents
        try:
            rows = soup.find('table', {'class': 'torrent-list'}).find('tbody').find_all('tr')
            for row in rows:
                title = row.find('a', {'href': lambda x: x.startswith('/view') and not x.endswith('#comments')})['title']
                magnet_link = row.find('a', {'href': lambda x: x.startswith('magnet')})['href']
                # td layout: [category, name, links*, size*, date*, seeds*, leechers*, downloads*]
                # `find('td', .text-center)` lands on the links cell (first centered).
                links_cell = row.find('td', {'class': 'text-center'})
                size_cell = links_cell.find_next_sibling('td')
                seed_cell = size_cell.find_next_sibling('td').find_next_sibling('td')
                size = size_cell.get_text(strip=True)
                seed_text = seed_cell.get_text(strip=True)
                seeds = int(seed_text) if seed_text.isdigit() else 0
                torrents.append([title, magnet_link, size, seeds])
        except Exception as e:
            print(f"Error parsing nyaa.si: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Network error in get_nyaa_search_result: {e}")
        return []
    return torrents


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


def get_season(url):
    season = 1
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            try:
                active_slide = soup.select_one('div.swiper-slide.aitem.active, div.swiper-slide.active')
                if active_slide:
                    season_text = active_slide.select_one('div.detail span').text.strip()
                    season = int(season_text.split(' ')[1])
            except Exception as e:
                season = 1
                print(f"Error parsing season: {e}")
    except Exception as e:
        print(f"Error getting season: {e}")
    return season

def get_watch_url(title):
    watch_url = 'https://animekai.to'
    try:
        url = 'https://animekai.to/ajax/anime/search'
        params = {'keyword': title}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get('status') in ('ok', 200) and data.get('result', {}).get('html'):
            soup = BeautifulSoup(data['result']['html'], 'html.parser')
            first_item = soup.find('a', {'class': 'aitem'})
            if first_item and 'href' in first_item.attrs:
                href_path = first_item['href']
                watch_url = 'https://animekai.to' + href_path
    except Exception as e:
        print(f"Error getting watch url: {e}")
    return watch_url


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
    
from pathlib import Path   
def get_r_path(path):
    return str(Path(__file__).joinpath("../../../resources").resolve().joinpath(path))
   

