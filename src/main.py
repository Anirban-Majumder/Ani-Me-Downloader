import requests
import sys
from utils import *
import constants
import logging
#logging.basicConfig(filename='data/log.txt', encoding='utf-8', level=logging.DEBUG)


class Anime:
    def __init__(self, id=0, name='', airing=False, total_episodes=1,last_aired_episode=1,
                 format='', output_dir='', img='', watch_url=[], season=1,
                 episodes_to_download=[], episodes_downloading=[],episodes_downloaded=[]):
        self.id = id
        self.name = name
        self.airing = airing
        self.total_episodes = total_episodes
        self.last_aired_episode = last_aired_episode
        self.season = season
        self.format = format
        self.output_dir = output_dir
        self.img = img
        self.watch_url = watch_url
        self.episodes_to_download = episodes_to_download
        self.episodes_downloading = episodes_downloading
        self.episodes_downloaded = episodes_downloaded

    def start(self):
        print(constants.line)
        print(f"Looking into {self.name}")
        if self.episodes_downloading:
            self.check_downloading()

        if self.airing:
            self.check_currently_airring()
            self.download_episodewise()
        else:
            if self.episodes_to_download:
                if not self.download_full():
                    self.download_episodewise()

        if self.episodes_downloaded and not self.episodes_to_download and not self.episodes_downloading:
            print(f"Downloaded {self.name}")
        elif self.airing and self.episodes_downloaded:
            print(f"Downloaded {self.name} till episode {len(self.episodes_downloaded)}")

    def download_episodewise(self):
        not_failed = True
        while self.episodes_to_download and self.episodes_to_download[0] <= self.last_aired_episode and not_failed:
            not_failed = self.download_episode(self.episodes_to_download[0])

    def download_episode(self, episode_number):
        magnet = ''
        name = self.name
        print(f"Looking for {name} episode {episode_number}")
        list = get_nyaa_search_result(name)
        if list == None:
            print(f"Torrent not found for {name} episode {episode_number}")
            return False
        for title, magnet_link in list:
            if '1080p' in title.lower():
                if '[subsplease]' in title.lower():
                    e = (' - ' + str(episode_number) if episode_number > 9 else (' - 0' + str(episode_number)))
                    s=(' S'+ str(self.season) if self.season >= 2 else '')
                    name = self.name + s + e
                    if name.lower() in title.lower():
                        magnet = magnet_link
                        break
                elif '[ember]' in title.lower():
                    additional = ('S'+ str(self.season) if self.season > 9 else 'S0' + str(self.season))+('E'+str(episode_number) if episode_number > 9 else 'E0'+str(episode_number))
                    if name.lower() in title.lower() and additional.lower() in title.lower():
                        magnet = magnet_link
                        break
        if not magnet:
            print("Torrent not found from subsplease or ember")
            choice = make_choice(list)
            if not choice:
                return False
            magnet = list[choice][1]
        self.download_from_magnet(magnet)
        self.episodes_downloading.append((episode_number, magnet))
        self.episodes_to_download.pop(0)
        return True

    def download_full(self):
        magnet = ''
        season = f'(Season {self.season})'
        name = self.name
        print(f"Looking for {name}")
        list = get_nyaa_search_result(name)
        if list == None:
            print(f"Torrent not found for {name}")
            return False
        if self.format == 'MOVIE':
            season = ' '
        for title, magnet_link in list:
            if '1080p' in title.lower():
                if any(keyword in title.lower() for keyword in ['[ember]', '[judas]', '[subsplease]']):
                    if '[ember]' or '[judas]' and season in title.lower():
                        magnet = magnet_link
                        break
                    elif '[subsplease]' in title.lower() and f'(01-{self.total_episodes})' in title.lower():
                        magnet = magnet_link
                        break
        if not magnet:
            print("Torrent not found from judas or ember or subsplease")
            choice = make_choice(list)
            if not choice:
                return False
            magnet = list[choice][1]
        self.download_from_magnet(magnet)
        self.episodes_to_download = []
        self.episodes_downloading.append(('full', magnet))
        return True

    def download_from_magnet(self, magnet_link) -> None:
        download_data = {'urls': magnet_link, 'savepath': self.output_dir}
        requests.post(f"{constants.qbit_url}/api/v2/torrents/add", data=download_data)
        print("Download started")

    def check_downloading(self):
        torrents = requests.get(f"{constants.qbit_url}/api/v2/torrents/info").json()
        if self.episodes_downloading:
            for episode_number, magnet_link in self.episodes_downloading:
                magnet_torrent = next((torrent for torrent in torrents if compare_magnet_links(torrent['magnet_uri'], magnet_link)), None)
                torrent_name = magnet_torrent['name']
                if magnet_torrent and magnet_torrent['state'] == "stalledUP" or magnet_torrent['state'] == "seeding":
                    self.episodes_downloading.remove([episode_number, magnet_link])
                    self.episodes_downloaded.append(episode_number)
                    print(f"{torrent_name} has finished downloading")
                    requests.post(f"{constants.qbit_url}/api/v2/torrents/pause", data={'hashes': magnet_torrent['hash']})
                else:
                    print(f"{torrent_name} is \n{(magnet_torrent['progress'] * 100):.2f}% done & has {(magnet_torrent['eta']/60):.2f} mins left")

    def check_currently_airring(self) -> None:
        query = constants.airring_query

        variables = {
            'id': self.id
        }

        url = constants.api_url

        response = requests.post(url, json={'query': query, 'variables': variables})
        data = json.loads(response.text)

        if self.airing:
            if data['data']['Media']['nextAiringEpisode'] == None:
                print(f"{self.name} has finished airing")
                self.last_aired_episode = self.total_episodes
            else:
                self.last_aired_episode = data['data']['Media']['nextAiringEpisode']['episode'] - 1
                print (f"{self.name} episode {self.last_aired_episode} is airing")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'season': self.season,
            'airing': self.airing,
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

def add_anime():
    title = input(constants.line+'\nEnter Anime Name: ')
    if not title or ("python.exe" in title.lower()):
        return

    res = get_anime_list(title)
    print(res)
    if not res:
        print("Anime not found\n" + constants.inp_err)
        return

    print("Choose the anime you want to download: ")
    start_index = 0
    end_index = min(len(res), 4)
    while True:
        for i in range(start_index, end_index):
            name = res[i]["title"]["romaji"]
            print(f"{i + 1}. {name}")
        print(f"{end_index + 1}. Show more")
        print(f"{end_index + 2}. None of the above")

        choice = input("Enter your choice: ")
        if not choice.isdigit():
            return
        choice = int(choice)
        if choice >= end_index + 2 or choice < 1:
            return
        elif choice == end_index + 1:
            start_index += 4
            end_index = min(len(res), end_index + 4)
        else:
            break
    return get_anime_detail(res[choice - 1])

def check_network():
    try:
        requests.get(ping)
    except Exception as e:
        logging.error(e)
        exit()

def load_anime_file():
    try:
        animes = load_animes(Anime, file)
    except FileNotFoundError:
        logging.error("Anime file not found")
        animes = []
    return animes

def start_animes(animes):
    for anime in animes:
        anime.start()

def save_anime_file(animes):
    if animes:
        save_animes(animes, file)

def main():
    check_network()
    animes = load_anime_file()
    start_animes(animes)
    save_anime_file(animes)

def new():
    check_network()
    animes = load_anime_file()
    start_animes(animes)
    save_anime_file(animes)

    detail = add_anime()
    if not detail:
        print(constants.inp_err)
        exit()
    new_anime = Anime(**detail)
    new_anime.start()
    animes.append(new_anime)

    save_anime_file(animes)
if __name__ == '__main__':
    args = sys.argv
    config = configparser.ConfigParser()
    config.read('data/config.ini')
    file = config['DEFAULT']['anime_file']
    ping = config['DEFAULT']['ping_url']
    if len(args) > 1 and args[1] == "regular":
        main()
    else:
       new()


#get season number if its not in the title
#check for disk space
#update it when completed