# coding:utf-8
class Constants:
    inp_err = "#### ENTER THE PROPER NAME OF THE ANIME AND CHOOSE FROM THE LIST ####"
    net_err = "#### NO INTERNET CONNECTION, PLEASE CONNECT TO INTERNET AND TRY AGAIN ####"
    line = "-"*50
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