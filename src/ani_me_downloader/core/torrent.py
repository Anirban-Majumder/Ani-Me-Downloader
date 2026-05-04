# coding: utf-8
"""Torrent dataclass + status/file enums. No PyQt, no libtorrent."""
from dataclasses import dataclass, field
from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass


class TorrentStatus(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    VERIFYING = "verifying"
    SEEDING = "seeding"
    COMPLETED = "completed"
    ERROR = "error"


class FilePriority(StrEnum):
    SKIP = "skip"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class TorrentFile:
    path: str
    size_bytes: int
    progress: float
    priority: FilePriority
    remaining_bytes: int


@dataclass
class Torrent:
    """info_hash is the primary key. Runtime fields are not persisted."""
    info_hash: str
    magnet: str
    name: str
    save_path: str
    anime_ids: set[int] = field(default_factory=set)
    desired_state: TorrentStatus = TorrentStatus.DOWNLOADING

    progress: float = 0.0
    size_bytes: int = 0
    eta: int = 0
    seeds: int = 0
    peers: int = 0
    dl_speed: int = 0
    ul_speed: int = 0
    files: list[TorrentFile] = field(default_factory=list)
