# coding: utf-8
"""Watch-URL resolvers. Parallel lookup across multiple streaming/aggregator
sites; each provider returns a deep link if its API works, else a search URL.
Providers whose host is unreachable from this network are dropped."""
from __future__ import annotations

import socket
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import requests
from bs4 import BeautifulSoup

ANIMEKAI_BASE = "https://animekai.to"
ANIMEPAHE_BASE = "https://animepahe.pw"
CINEBY_BASE = "https://www.cineby.app"
MIRURO_BASE = "https://www.miruro.tv"

_REACH_TIMEOUT = 2.0
_API_TIMEOUT = 6.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _quote(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _reachable(host: str, port: int = 443) -> bool:
    """Fast TCP probe. Doesn't speak TLS — just confirms the host accepts
    connections, which is all 'functional from this network' really means."""
    try:
        with socket.create_connection((host, port), timeout=_REACH_TIMEOUT):
            return True
    except OSError:
        return False


def _animekai_deep(title: str) -> str | None:
    r = requests.get(
        f"{ANIMEKAI_BASE}/ajax/anime/search",
        params={"keyword": title},
        headers={**_HEADERS, "Referer": ANIMEKAI_BASE + "/"},
        timeout=_API_TIMEOUT,
    )
    data = r.json()
    if data.get("status") not in ("ok", 200):
        return None
    html = data.get("result", {}).get("html") or ""
    soup = BeautifulSoup(html, "html.parser")
    a = soup.find("a", {"class": "aitem"})
    if a and a.get("href"):
        return ANIMEKAI_BASE + a["href"]
    return None


def _animepahe_deep(title: str) -> str | None:
    """animepahe's /api gates on X-Requested-With + Referer; without those it
    returns the cloudflare HTML challenge instead of JSON."""
    r = requests.get(
        f"{ANIMEPAHE_BASE}/api",
        params={"m": "search", "q": title},
        headers={
            **_HEADERS,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": ANIMEPAHE_BASE + "/",
        },
        timeout=_API_TIMEOUT,
    )
    data = r.json()
    results = data.get("data") or []
    if not results:
        return None
    session = results[0].get("session")
    if not session:
        return None
    return f"{ANIMEPAHE_BASE}/anime/{session}"


# Search-URL fallbacks — used when the API fails / has no public API.
# These open the site's actual search page so the user can pick manually.
_SEARCH_URL = {
    "animekai": lambda t: f"{ANIMEKAI_BASE}/browser?keyword={_quote(t)}",
    "animepahe": lambda t: f"{ANIMEPAHE_BASE}/anime?q={_quote(t)}",
    "cineby": lambda t: f"{CINEBY_BASE}/search?q={_quote(t)}",
    "miruro": lambda t: f"{MIRURO_BASE}/search?query={_quote(t)}&type=ANIME&sort=POPULARITY_DESC",
}

# Optional deep-link resolvers. Missing entry = search URL only (cineby, miruro
# have no public per-anime API we can hit reliably).
_DEEP: dict[str, Callable[[str], str | None]] = {
    "animekai": _animekai_deep,
    "animepahe": _animepahe_deep,
}

_HOSTS = {
    "animekai": "animekai.to",
    "animepahe": "animepahe.pw",
    "cineby": "www.cineby.app",
    "miruro": "www.miruro.tv",
}


def _resolve_one(name: str, title: str) -> str | None:
    """Return best URL for one provider, or None if host unreachable."""
    if not _reachable(_HOSTS[name]):
        return None
    deep_fn = _DEEP.get(name)
    if deep_fn is not None:
        try:
            url = deep_fn(title)
            if url:
                return url
        except Exception as exc:
            print(f"{name} deep-link failed, falling back to search: {exc}")
    return _SEARCH_URL[name](title)


def get_watch_urls(title: str) -> dict[str, str]:
    """Run every provider in parallel. Returns provider→URL for hosts that
    are reachable. Each entry is a deep-link if the API yielded one, else
    the provider's search URL pre-filled with the title."""
    if not title:
        return {}
    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(_HOSTS)) as pool:
        futures = {pool.submit(_resolve_one, name, title): name for name in _HOSTS}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                url = fut.result()
            except Exception as exc:
                print(f"{name} resolver crashed: {exc}")
                url = None
            if url:
                out[name] = url
    return out


def get_season(url: str) -> int:
    """Animekai-only season parser. Returns 1 for any other host or on failure."""
    if not url or "animekai" not in url:
        return 1
    season = 1
    try:
        r = requests.get(url, timeout=_API_TIMEOUT, headers=_HEADERS)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            try:
                active = soup.select_one(
                    "div.swiper-slide.aitem.active, div.swiper-slide.active"
                )
                if active:
                    text = active.select_one("div.detail span").text.strip()
                    season = int(text.split(" ")[1])
            except Exception as e:
                season = 1
                print(f"Error parsing season: {e}")
    except Exception as e:
        print(f"Error getting season: {e}")
    return season
