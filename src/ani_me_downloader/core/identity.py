# coding: utf-8
"""Magnet infohash extraction + comparison."""
from urllib.parse import parse_qs, urlparse


def info_hash_from_magnet(magnet: str) -> str | None:
    """Lowercase hex infohash from a magnet URI, or None if unparseable."""
    if not magnet:
        return None
    xt = parse_qs(urlparse(magnet).query).get("xt", [""])[0]
    if not xt.startswith("urn:btih:"):
        return None
    return xt.removeprefix("urn:btih:").lower()


def magnets_match(a: str, b: str) -> bool:
    h = info_hash_from_magnet(a)
    return h is not None and h == info_hash_from_magnet(b)
