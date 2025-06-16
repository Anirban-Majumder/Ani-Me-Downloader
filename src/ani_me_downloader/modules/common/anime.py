# coding:utf-8
import requests
import time
import re

from PyQt5.QtCore import QObject, pyqtSignal

from .utils import (
    Constants,
    remove_non_alphanum,
    compare_magnet_links,
    get_nyaa_search_result,
    get_time_diffrence,
    check_network
)


class Anime(QObject):
    """Class for managing the download of anime episodes or seasons."""
    infoSignal = pyqtSignal(str)
    errorSignal = pyqtSignal(str)
    successSignal = pyqtSignal(str)
    selectionSignal = pyqtSignal(list)
    addTorrentSignal = pyqtSignal(dict)

    def __init__(self, **kwargs):
        """Initialize an instance of the Anime class."""

        super().__init__()

        self.id = kwargs.get('id', 0)
        self.idMal = kwargs.get('idMal', 0)
        self.name = kwargs.get('name', '')
        self.search_name = kwargs.get('search_name', '')
        self.airing = kwargs.get('airing', False)
        self.next_eta = kwargs.get('next_eta', 0)
        self.total_episodes = kwargs.get('total_episodes', 1)
        self.last_aired_episode = (
            kwargs.get('last_aired_episode') if self.airing else self.total_episodes
        )
        self.season = kwargs.get('season', 1)
        self.format = kwargs.get('format', '')
        self.output_dir = kwargs.get('output_dir', '')
        self.img = kwargs.get('img', '')
        self.watch_url = kwargs.get('watch_url', '')
        self.episodes_to_download = kwargs.get('episodes_to_download', [])
        self.episodes_downloading = kwargs.get('episodes_downloading', [])
        self.episodes_downloaded = kwargs.get('episodes_downloaded', [])
        self.batch_download = kwargs.get('batch_download', True)
        self.watch_url = kwargs.get('watch_url', '')
        self.result = None

    def start(self):
        """Start downloading episodes or the entire season."""
        print('-'*80)
        print(f'Looking into {self.name}')

        if self.airing:
            self.check_currently_airing()

        if self.episodes_to_download:
            if self.batch_download:
                self.download_full()
            else:
                self.download_episodes()

        if (self.episodes_downloaded and
            not self.episodes_to_download and
            not self.episodes_downloading):
            print(f'Downloaded {self.name} completely.')
        elif self.airing and self.episodes_downloaded:
            downloaded_episodes = len(self.episodes_downloaded)
            print(f'Downloaded {self.name} till episode {downloaded_episodes}.')

    def download_full(self):
        """Download the full batch at once."""
        self.infoSignal.emit(f'Looking for {self.name}...')

        if self.airing:
            self.infoSignal.emit(f'{self.name} is still airing...')
            return False

        self.infoSignal.emit('searching')
        torrents = self.get_torrent_list()
        print(f"Found {len(torrents)} torrents")
        self.errorSignal.emit('searching')

        if not torrents:
            self.errorSignal.emit('No torrent found!')
            return False
        magnet = self.select_torrent(torrents)

        if not magnet:
            self.selectionSignal.emit([self.id, torrents])
            return False

        self.download_from_magnet(magnet, self.name)
        self.episodes_to_download = []
        self.episodes_downloading.append(('full', magnet))
        return True

    def download_episodes(self):
        """Download episodes one by one."""
        not_failed = True
        while (
            not_failed
            and self.episodes_to_download  # Check if list is not empty
            and self.episodes_to_download[0] <= self.last_aired_episode
        ):
            not_failed = self.download_episode(self.episodes_to_download[0])

    def download_episode(self, episode_number):
        """Download a single episode."""
        name = f'{self.name} S{self.season:02d}E{episode_number:02d}'
        self.infoSignal.emit(f'Looking for {name}')

        self.infoSignal.emit('searching')

        if not self.result:
            self.result = self.get_torrent_list()
        print(f"Found {len(self.result)} torrents")

        self.errorSignal.emit('searching')

        if not self.result:
            self.errorSignal.emit(f'No torrent found for {name}')
            return False

        magnet = self.select_torrent(self.result, episode_number)

        if not magnet:
            print(f'Torrent not found from preferred uploaders! for episode {episode_number}')
            self.errorSignal.emit('Torrent not found from preferred uploaders!')
            return False

        self.download_from_magnet(magnet, name)
        self.episodes_downloading.append((episode_number, magnet))
        print(episode_number, 'added to episodes_downloading')#, self.episodes_to_download)
        self.episodes_to_download.remove(episode_number)

        if episode_number == self.total_episodes:
            return False

        return True

    def download_from_magnet(self, magnet_link, name):
        """Download a file using a magnet link.

        Args:
            magnet_link (str): The magnet link to use for the download.
            name (str): The name of the file being downloaded.
        """
        # Create torrent info and emit signal to add it
        torrent_info = {
            'name': name,
            'magnet': magnet_link,
            'path': self.output_dir,
            'anime_id': self.id,
            'status': 'downloading'
        }

        self.addTorrentSignal.emit(torrent_info)
        self.successSignal.emit(f'Download started {name}')
 
    def get_torrent_list(self, retry_count=2):
        """Get a list of torrents for the given name.

        Args:
            retry_count (int): The number of times to retry the search if no results are found.

        Returns:
            list: A list of tuples containing the title, magnet link, and size of torrents.
        """
        for _ in range(retry_count):

            torrents = get_nyaa_search_result(self.search_name) if self.search_name==self.name else [list(item) for item in set(tuple(x) for x in (get_nyaa_search_result(self.search_name) + get_nyaa_search_result(self.name)))]
            if torrents:
                return torrents

            self.infoSignal.emit('No result found... Trying Again...')
            if not check_network():
                self.errorSignal.emit('Internet connection not available!')
                exit()

        self.errorSignal.emit('Either the anime is not available or the name is wrong!')
        return []

    def select_torrent(self, torrents, episode_number="batch"):
        """Select the best torrent from a list of torrents.

        Args:
            torrents (list): A list of tuples containing the title, magnet link, and size of each torrent.
                The list should be already sorted by seeds.
            episode_number (int): The episode number to download. Default is batch which means download the full batch.

        Returns:
            str: The magnet link of the selected torrent.
        """
        name = re.escape(self.name)
        search_name = re.escape(self.search_name)
        season = f'(season {self.season})' if self.format != 'movie' else ''

        pattern = rf'\b(1080p.*({name}|{search_name})|({name}|{search_name}).*1080p)\b'
        regex = re.compile(pattern, re.IGNORECASE)

        if isinstance(episode_number, int):
            for title, magnet_link, size in torrents:
                if regex.search(title) and 'vostfr' not in title.lower():
                    title_lower = title.lower()
                    if '[ember]' in title_lower:
                        additional = f' s{self.season:02}e{episode_number:02} '
                        if additional in title_lower:
                            return magnet_link
                    elif '[subsplease]' in title_lower:
                        additional = f'{" s " + str(self.season) if self.season >= 2 else ""} - {episode_number:02} '
                        if additional in title_lower:
                            return magnet_link
                    elif '[erai-raws]' in title_lower:
                        additional = f'{episode_number:02} '
                        if additional in title_lower:
                            return magnet_link
                    elif '[toonshub]' in title_lower:
                        additional = f'e{episode_number} '
                        if additional in title_lower:
                            return magnet_link
                    else:
                        additional = f' s{self.season:02}e{episode_number:02} ' if self.season >= 2 else f' e{episode_number:02} '
                        if additional in title_lower:
                            return magnet_link
                        additional = f' s{self.season:02}e{episode_number:02} '
                        if additional in title_lower:
                            return magnet_link

        else:
            for title, magnet_link, size in torrents:
                if regex.search(title):
                    title_lower = title.lower()
                    if any(keyword in title_lower for keyword in ['[ember]', '[judas]', '[subsplease]']):
                        if any(keyword in title_lower for keyword in ['batch', 'complete']):
                            if season in title_lower:
                                return magnet_link


        return ''

    def receive_data(self, data):
        """Receive data from an external source.

        Args:
            data (list): A list containing the name and magnet link of a file to download.
        """
        if not data:
            return
        name, magnet, size = data
        self.download_from_magnet(magnet, name)
        self.episodes_to_download = []
        self.episodes_downloading.append(('full', magnet))

    def check_currently_airing(self):
        """Check if the anime is still airing and update the next_eta, last_aired_episode, and total_episodes attributes accordingly."""
        current_time = int(time.time())

        if self.next_eta > current_time:
            days, hours, minutes = get_time_diffrence(self.next_eta)
            print(
                f'Next episode airing in about {days} days {hours} hrs {minutes} mins'
            )
            return

        query = Constants.airing_query
        variables = {'id': self.id}
        url = Constants.api_url
        response = requests.post(url, json={'query': query, 'variables': variables})
        data = response.json()

        if data['data']['Media']['nextAiringEpisode'] is None:
            print(f'{self.name} has finished airing!')
            self.infoSignal.emit(f'{self.name} has finished airing!')
            self.last_aired_episode = self.total_episodes
            self.airing = False
            self.next_eta = 0
        else:
            self.next_eta = data['data']['Media']['nextAiringEpisode']['airingAt']
            self.last_aired_episode = (
                data['data']['Media']['nextAiringEpisode']['episode'] - 1
            )
            print(f'{self.name} episode {self.last_aired_episode} is airing')

    def to_dict(self):
        """Convert the Anime instance to a dictionary.

        Returns:
            dict: A dictionary representation of the Anime instance.
        """
        return {
            'id': self.id,
            'idMal': self.idMal,
            'name': self.name,
            'search_name': self.search_name,
            'season': self.season,
            'airing': self.airing,
            'batch_download': self.batch_download,
            'next_eta': self.next_eta,
            'format': self.format,
            'last_aired_episode': self.last_aired_episode,
            'total_episodes': self.total_episodes,
            'output_dir': self.output_dir,
            'watch_url': self.watch_url,
            'img': self.img,
            'episodes_to_download': self.episodes_to_download,
            'episodes_downloading': self.episodes_downloading,
            'episodes_downloaded': self.episodes_downloaded
        }

    @classmethod
    def from_dict(cls, data):
        """Create an Anime instance from a dictionary.

        Args:
            data (dict): A dictionary containing the data for the Anime instance.

        Returns:
            Anime: An Anime instance initialized with the given data.
        """
        return cls(**data)
