# coding: utf-8
"""Typed commands consumed by the TorrentThread."""
from dataclasses import dataclass
from typing import Union

from ..core.torrent import FilePriority, Torrent


@dataclass(frozen=True)
class AddTorrent:
    torrent: Torrent


@dataclass(frozen=True)
class RemoveTorrent:
    info_hash: str
    delete_files: bool = False


@dataclass(frozen=True)
class PauseTorrent:
    info_hash: str


@dataclass(frozen=True)
class ResumeTorrent:
    info_hash: str


@dataclass(frozen=True)
class SetFilePriority:
    info_hash: str
    file_index: int
    priority: FilePriority


Command = Union[AddTorrent, RemoveTorrent, PauseTorrent, ResumeTorrent, SetFilePriority]
