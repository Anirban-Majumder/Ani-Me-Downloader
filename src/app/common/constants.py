# coding:utf-8
class Constants:
    nineanime_url = 'https://9anime.pl'
    api_url = 'https://graphql.anilist.co'
    qbit_url = 'http://localhost:8080'
    proxy_url ='https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=5000&country=all'
    airring_query = '''
    query ($id: Int) {
      Media(id: $id, type: ANIME) {
        id
        status
        nextAiringEpisode {
            airingAt
            episode
        }
      }
    }
    '''
    list_query = '''
    query ($search: String) {
      Page {
        media(search: $search, type: ANIME) {
          id
          title {
            romaji
          }
          format
          status
          episodes
          nextAiringEpisode {
            episode
            airingAt
        }
          coverImage {
            extraLarge
          }
        }
      }
    }
    '''