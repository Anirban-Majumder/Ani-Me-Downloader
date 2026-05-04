# coding: utf-8
"""Nyaa.si torrent scraping. Pure function; takes use_proxy as a param."""
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

NYAA_URL = "https://nyaa.si"
PROXY_URL = "https://ani-me-downloader-proxy.vercel.app"


@dataclass
class NyaaResult:
    title: str
    magnet: str
    size: str
    seeds: int


def search_nyaa(query: str, *, use_proxy: bool, timeout: int = 10) -> list[NyaaResult]:
    """Scrape Nyaa torrent rows for `query`. Returns seed-sorted descending."""
    base = PROXY_URL if use_proxy else NYAA_URL
    params = {"f": "0", "c": "1_0", "q": query, "s": "seeders", "o": "desc"}
    try:
        response = requests.get(base, params=params, timeout=timeout)
    except requests.exceptions.RequestException as e:
        print(f"Network error in search_nyaa: {e}")
        return []
    print("Request URL:", response.url)
    if not response:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    if "No results found" in soup.text:
        return []

    out: list[NyaaResult] = []
    try:
        rows = soup.find("table", {"class": "torrent-list"}).find("tbody").find_all("tr")
    except AttributeError:
        return []
    for row in rows:
        try:
            title = row.find(
                "a",
                {"href": lambda x: x.startswith("/view") and not x.endswith("#comments")},
            )["title"]
            magnet = row.find("a", {"href": lambda x: x.startswith("magnet")})["href"]
            # td layout: [category, name, links*, size*, date*, seeds*, leechers*, downloads*]
            links_cell = row.find("td", {"class": "text-center"})
            size_cell = links_cell.find_next_sibling("td")
            seed_cell = size_cell.find_next_sibling("td").find_next_sibling("td")
            size = size_cell.get_text(strip=True)
            seed_text = seed_cell.get_text(strip=True)
            seeds = int(seed_text) if seed_text.isdigit() else 0
            out.append(NyaaResult(title=title, magnet=magnet, size=size, seeds=seeds))
        except Exception as e:
            print(f"Error parsing nyaa.si row: {e}")
    return out
