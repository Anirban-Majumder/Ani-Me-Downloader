# coding: utf-8
"""Data-driven uploader-tag rules used by the selector."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UploaderRule:
    """Per-uploader title patterns. Tag matched lowercase against the title."""
    tag: str
    episode_pattern: str
    batch_keywords: tuple[str, ...] = ("batch", "complete")
    accepts_batch: bool = False
    accepts_episodes: bool = True


DEFAULT_RULES: tuple[UploaderRule, ...] = (
    UploaderRule("[ember]",      " s{season:02}e{episode:02} ", accepts_batch=True),
    UploaderRule("[subsplease]", " - {episode:02} "),
    UploaderRule("[erai-raws]",  "{episode:02} "),
    UploaderRule("[toonshub]",   "e{episode} "),
    UploaderRule("[judas]",      " s{season:02}e{episode:02} ", accepts_batch=True),
)
