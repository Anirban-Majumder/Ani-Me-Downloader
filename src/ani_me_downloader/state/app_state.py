# coding: utf-8
"""In-memory canonical state plus persistence binding."""
from ..core.anime import Anime, EpStatus
from ..core.torrent import Torrent
from ..persistence.anime_repo import AnimeRepository
from ..persistence.torrent_repo import TorrentRepository


class AppState:
    """Owns the canonical animes/torrents lists and their repositories."""

    def __init__(
        self,
        animes: list[Anime],
        torrents: list[Torrent],
        anime_repo: AnimeRepository,
        torrent_repo: TorrentRepository,
    ):
        self.animes = animes
        self.torrents = torrents
        self._anime_repo = anime_repo
        self._torrent_repo = torrent_repo

    @classmethod
    def load(cls, anime_repo: AnimeRepository, torrent_repo: TorrentRepository) -> "AppState":
        return cls(
            animes=anime_repo.load(),
            torrents=torrent_repo.load(),
            anime_repo=anime_repo,
            torrent_repo=torrent_repo,
        )

    def add_anime(self, a: Anime) -> None:
        self.animes.insert(0, a)

    def remove_anime(self, id: int) -> Anime | None:
        for i, a in enumerate(self.animes):
            if a.id == id:
                return self.animes.pop(i)
        return None

    def get_anime(self, id: int) -> Anime | None:
        return next((a for a in self.animes if a.id == id), None)

    def add_torrent(self, t: Torrent) -> Torrent:
        """Add or merge owners. Returns the canonical row."""
        for existing in self.torrents:
            if existing.info_hash == t.info_hash:
                existing.anime_ids |= t.anime_ids
                return existing
        self.torrents.append(t)
        return t

    def remove_torrent(self, info_hash: str) -> Torrent | None:
        for i, t in enumerate(self.torrents):
            if t.info_hash == info_hash:
                return self.torrents.pop(i)
        return None

    def get_torrent(self, info_hash: str) -> Torrent | None:
        return next((t for t in self.torrents if t.info_hash == info_hash), None)

    def save_animes(self) -> None:
        self._anime_repo.save(self.animes)

    def save_torrents(self) -> None:
        self._torrent_repo.save(self.torrents)

    def reconcile(self) -> int:
        """Recreate Torrent rows for in-flight EpStates that lost them."""
        from ..core.identity import info_hash_from_magnet
        from ..core.torrent import TorrentStatus
        from ..core.episodes import episode_display_name

        added = 0
        for anime in self.animes:
            for ep in anime.episodes:
                if ep.status not in (EpStatus.DOWNLOADING, EpStatus.BATCH_PENDING):
                    continue
                if not ep.magnet:
                    continue
                ih = info_hash_from_magnet(ep.magnet)
                if not ih:
                    continue
                existing = self.get_torrent(ih)
                if existing is not None:
                    existing.anime_ids.add(anime.id)
                    continue
                t = Torrent(
                    info_hash=ih,
                    magnet=ep.magnet,
                    name=episode_display_name(anime, ep.ep),
                    save_path=anime.output_dir,
                    anime_ids={anime.id},
                    desired_state=TorrentStatus.DOWNLOADING,
                )
                self.torrents.append(t)
                added += 1
        if added:
            print(f"[reconcile] Recovered {added} missing torrent(s).")
        return added
