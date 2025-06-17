
import requests
false = False
d={
        "id": 177709,
        "idMal": 58939,
        "name": "SAKAMOTO DAYS",
        "search_name": "SAKAMOTO DAYS",
        "season": 1,
        "airing": false,
        "batch_download": false,
        "next_eta": 0,
        "format": "ONA",
        "last_aired_episode": 11,
        "total_episodes": 11,
        "output_dir": "/home/anirban/Downloads/SAKAMOTO DAYS",
        "watch_url": "https://animekai.to/watch/sakamoto-days-qx1r",
        "img": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx177709-jBQ965JZG0l8.png",
        "episodes_to_download": [],
        "episodes_downloading": [
            [
                5,
                "magnet:?xt=urn:btih:4169dee3dbdd7627041807138327cfc592772401&dn=SAKAMOTO%20DAYS%20S01E05%20Source%20of%20Strength%201080p%20NF%20WEB-DL%20DDP5.1%20H%20264%20MULTi-VARYG%20%28Multi-Audio%2C%20Multi-Subs%29&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce"
            ]
        ],
        "episodes_downloaded": []
    }
def get_latest_anime_info(anime_id):
    url = "https://graphql.anilist.co"
    query = """
    query ($id: Int) {
      Media(id: $id) {
        idMal
        title {
          english
        }
        nextAiringEpisode {
          episode
          timeUntilAiring
        }
        status
        description
      }
    }
    """
    variables = {"id": anime_id}
    response = requests.post(url, json={"query": query, "variables": variables})
    data = response.json()
    print(data)
    
    if "data" in data and data["data"]["Media"]["nextAiringEpisode"]:
        return {
            "title": data["data"]["Media"]["title"]["english"],
            "next_episode": data["data"]["Media"]["nextAiringEpisode"]["episode"],
            "airing_in": data["data"]["Media"]["nextAiringEpisode"]["timeUntilAiring"],
            "status": data["data"]["Media"]["status"],
            "description": data["data"]["Media"]["description"]
        }
    else:
        return {"error": "No upcoming episode found."}

# Example Usage
anime_id = 176273  # Example Anime (Attack on Titan)
print(get_latest_anime_info(anime_id))
