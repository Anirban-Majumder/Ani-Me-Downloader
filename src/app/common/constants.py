class Constants:
    inp_err = "#### ENTER THE PROPER NAME OF THE ANIME AND CHOOSE FROM THE LIST ####"
    net_err = "#### NO INTERNET CONNECTION, PLEASE CONNECT TO INTERNET AND TRY AGAIN ####"
    line = "-"*50
    api_url = 'https://graphql.anilist.co'
    qbit_url = 'http://localhost:8080'
    airring_query = '''
    query ($id: Int) {
      Media(id: $id, type: ANIME) {
        id
        status
        nextAiringEpisode {
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
        }
          coverImage {
            extraLarge
          }
        }
      }
    }
    '''