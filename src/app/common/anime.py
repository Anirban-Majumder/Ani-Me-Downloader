# coding:utf-8
import requests, json, time
from .utils import constants, get_nyaa_search_result, compare_magnet_links
from PyQt5.QtCore import pyqtSignal, QObject

class SignalEmitter(QObject):
    infoSignal = pyqtSignal(str)
    errorSignal = pyqtSignal(str)
    successSignal = pyqtSignal(str)
    listSignal = pyqtSignal(list)


class Anime:
    def __init__(self, id=0, name='', airing=False, download_full=True, next_eta=0, total_episodes=1,last_aired_episode=1,
                 format='', output_dir='', img='', watch_url="", season=1,
                 episodes_to_download=[], episodes_downloading=[],episodes_downloaded=[]):
        self.id = id
        self.name = name
        self.airing = airing
        self.next_eta = next_eta
        self.total_episodes = total_episodes
        self.last_aired_episode = last_aired_episode if airing else total_episodes
        self.season = season
        self.format = format
        self.output_dir = output_dir
        self.img = img
        self.watch_url = watch_url
        self.episodes_to_download = episodes_to_download
        self.episodes_downloading = episodes_downloading
        self.episodes_downloaded = episodes_downloaded
        self.download_full = download_full
        self.result = None
        self.signal = SignalEmitter()

    def start(self):
        self.signal.infoSignal.emit(f"Looking into {self.name}")
        if self.episodes_downloading:
            self.check_downloading()

        if self.airing:
            self.check_currently_airring()


        if self.episodes_to_download:
            if self.download_full:
                self.download()
            else:
                self.download_episodewise()

        if self.episodes_downloaded and not self.episodes_to_download and not self.episodes_downloading:
            self.signal.successSignal.emit(f"Downloaded {self.name} completely.")
        elif self.airing and self.episodes_downloaded:
            self.signal.successSignal.emit(f"Downloaded {self.name} till episode {len(self.episodes_downloaded)}.")

    def download_episodewise(self):
        not_failed = True
        while not_failed and self.episodes_to_download[0] <= self.last_aired_episode :
            not_failed = self.download_episode(self.episodes_to_download[0])

    def download_episode(self, episode_number):
        magnet = ''
        list = self.result if self.result else self.get_torrent_list(self.name)
        name = self.name
        self.signal.infoSignal.emit(f"Looking for {name} episode {episode_number}...")
        if not list:
            return False
        for title, magnet_link, size in list:
            if '1080p' in title.lower():
                if '[ember]' in title.lower():
                    additional = ('S'+ str(self.season) if self.season > 9 else 'S0' + str(self.season))+('E'+str(episode_number) if episode_number > 9 else 'E0'+str(episode_number))
                    if name.lower() in title.lower() and additional.lower() in title.lower():
                        magnet = magnet_link
                        break
                elif '[subsplease]' in title.lower():
                    e = (' - ' + str(episode_number) if episode_number > 9 else (' - 0' + str(episode_number)))
                    s=(' S'+ str(self.season) if self.season >= 2 else '')
                    name = self.name + s + e
                    if name.lower() in title.lower():
                        magnet = magnet_link
                        break
        if not magnet:
            self.signal.errorSignal.emit("Torrent not found from subsplease or ember!")
            return False
        self.download_from_magnet(magnet)
        self.episodes_downloading.append((episode_number, magnet))
        i=self.episodes_to_download.pop(0)
        if i == self.total_episodes:
            return False
        return True

    def download(self):
        magnet = ''
        season = f'(Season {self.season})'
        name = self.name
        self.signal.infoSignal.emit(f"Looking for {name}...")
        list =  self.get_torrent_list(name)
        if not list:
            self.signal.errorSignal.emit("No torrent found!")
            return False
        if self.format == 'MOVIE':
            season = ' '
        for title, magnet_link, size in list:
            if '1080p' in title.lower():
                if any(keyword in title.lower() for keyword in ['[ember]', '[judas]', '[subsplease]']):
                    if '[ember]' or '[judas]' and season in title.lower():
                        magnet = magnet_link
                        break
                    elif '[subsplease]' in title.lower() and f'(01-{self.total_episodes})' in title.lower():
                        magnet = magnet_link
                        break
        if not magnet:
            self.signal.listSignal.emit([self.id,list])
            return False

        self.download_from_magnet(magnet)
        self.episodes_to_download = []
        self.episodes_downloading.append(('full', magnet))
        return True

    def download_from_magnet(self, magnet_link) -> None:
        download_data = {'urls': magnet_link, 'savepath': self.output_dir}
        requests.post(f"{constants.qbit_url}/api/v2/torrents/add", data=download_data)
        self.signal.successSignal.emit("Download started")

    def check_downloading(self):
        torrents = requests.get(f"{constants.qbit_url}/api/v2/torrents/info").json()
        if self.episodes_downloading:
            for episode_number, magnet_link in self.episodes_downloading:
                magnet_torrent = next((torrent for torrent in torrents if compare_magnet_links(torrent['magnet_uri'], magnet_link)), None)
                torrent_name = magnet_torrent['name']
                if magnet_torrent and magnet_torrent['state'] == "stalledUP" or magnet_torrent['state'] == "seeding":
                    self.episodes_downloading.remove([episode_number, magnet_link])
                    self.episodes_downloaded.append(episode_number)
                    self.signal.infoSignal.emit(f"{torrent_name} has finished downloading :)")
                    requests.post(f"{constants.qbit_url}/api/v2/torrents/pause", data={'hashes': magnet_torrent['hash']})
                else:
                    self.signal.infoSignal.emit(f"{torrent_name} is \n{(magnet_torrent['progress'] * 100):.2f}% done & has {(magnet_torrent['eta']/60):.2f} mins left !!")

    def check_currently_airring(self) -> None:

        self.download_full = False
        current_time = int(time.time())
        if  self.next_eta > current_time:
            time_difference = self.next_eta - current_time
            days = time_difference // (24 * 3600)
            time_difference = time_difference % (24 * 3600)
            hours = time_difference // 3600
            time_difference %= 3600
            minutes = time_difference // 60
            self.signal.infoSignal.emit(f"Next episode airing in about {days} days {hours} hrs {minutes} mins")
            return

        query = constants.airring_query

        variables = {
            'id': self.id
        }

        url = constants.api_url

        response = requests.post(url, json={'query': query, 'variables': variables})
        data = json.loads(response.text)

        if self.airing:
            if data['data']['Media']['nextAiringEpisode'] == None:
                self.signal.infoSignal.emit(f"{self.name} has finished airing!")
                self.last_aired_episode = self.total_episodes
                self.airing = False
                self.next_eta = 0
            else:
                self.next_eta = data['data']['Media']['nextAiringEpisode']['airingAt']
                self.last_aired_episode = data['data']['Media']['nextAiringEpisode']['episode'] - 1
                self.signal.infoSignal.emit(f"{self.name} episode {self.last_aired_episode} is airing")

    def get_torrent_list(self,name):
        list = get_nyaa_search_result(name)
        if not list:
            self.signal.errorSignal.emit(f"No result found...")
            self.signal.infoSignal.emit(f"Trying Again...")
            try:
                res=requests.get("https://www.google.com")
                res.raise_for_status()
            except Exception as e:
                self.signal.errorSignal.emit(f"Internet connection not available!")
                exit()
            list = get_nyaa_search_result(name)
            if not list:
                self.signal.errorSignal.emit(f"Either the anime is not available or the name is wrong...")
        return list

    def receiveData(self, data):
        print(data)
        if not data:
            return
        magnet= data[1]
        self.download_from_magnet(magnet)
        self.episodes_to_download = []
        self.episodes_downloading.append(('full', magnet))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'season': self.season,
            'airing': self.airing,
            'download_full': self.download_full,
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
        return cls(**data)


