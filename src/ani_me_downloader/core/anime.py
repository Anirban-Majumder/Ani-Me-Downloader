# coding: utf-8
"""Anime dataclass + episode/airing enums. No PyQt."""
from dataclasses import dataclass, field
from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass


class AnimeFormat(StrEnum):
    TV = "tv"
    MOVIE = "movie"
    OVA = "ova"
    ONA = "ona"
    SPECIAL = "special"
    UNKNOWN = "unknown"


class AiringStatus(StrEnum):
    RELEASING = "releasing"
    FINISHED = "finished"
    NOT_YET_RELEASED = "not_yet_released"
    HIATUS = "hiatus"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class EpStatus(StrEnum):
    """Persisted per-episode states. `queued` and `not_aired` are derived,
    not stored: an aired ep with no record is implicitly queued."""
    TRACK_ONLY = "track_only"
    DOWNLOADING = "downloading"
    DONE = "done"
    BATCH_PENDING = "batch_pending"
    BATCH_DONE = "batch_done"


class DownloadMode(StrEnum):
    BATCH = "batch"
    EPISODES = "episodes"
    TRACK_ONLY = "track_only"


@dataclass
class EpState:
    """Per-episode record. ep=0 is the synthetic batch entry.
    `magnet` is cleared once status becomes DONE / BATCH_DONE."""
    ep: int
    status: EpStatus
    magnet: str | None = None


@dataclass
class Anime:
    """Persisted anime record. id is the MAL id."""
    id: int
    name: str
    search_name: str = ""
    season: int = 1
    format: AnimeFormat = AnimeFormat.UNKNOWN
    output_dir: str = ""
    img: str = ""
    watch_urls: dict[str, str] = field(default_factory=dict)

    status: AiringStatus = AiringStatus.UNKNOWN
    next_eta: int = 0
    last_aired_episode: int = 0
    total_episodes: int = 1

    download_mode: DownloadMode = DownloadMode.EPISODES
    ep_from: int = 1
    ep_to: int = 0  # 0 means use total_episodes

    episodes: list[EpState] = field(default_factory=list)

    @property
    def is_airing(self) -> bool:
        return self.status is AiringStatus.RELEASING

    @property
    def is_done(self) -> bool:
        return self.status in (AiringStatus.FINISHED, AiringStatus.CANCELLED)

    @property
    def needs_metadata_refresh(self) -> bool:
        """Periodic tick only re-queries airing-relevant statuses."""
        return self.status in (
            AiringStatus.RELEASING,
            AiringStatus.NOT_YET_RELEASED,
            AiringStatus.HIATUS,
        )

    def pending_eps(self) -> list[int]:
        """Episode numbers that should be searched this tick. Lazy derivation:
        aired eps minus those with an existing record. ep=0 for batch shows."""
        known = {e.ep for e in self.episodes}
        if self.download_mode is DownloadMode.BATCH:
            return [] if 0 in known else [0]
        if self.download_mode is DownloadMode.TRACK_ONLY:
            return []
        upper = self.ep_to or self.total_episodes
        cap = min(self.last_aired_episode, upper)
        lower = max(1, self.ep_from)
        return [n for n in range(lower, cap + 1) if n not in known]
