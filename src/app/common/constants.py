# coding:utf-8
class Constants:
    nineanime_url = 'https://aniwave.to'
    nyaa_url = 'https://nyaa.si'
    api_url = 'https://graphql.anilist.co'
    qbit_url = 'http://localhost:8080'
    proxy_url ='https://ani-me-downloader-proxy.vercel.app/api'
    airing_query = '''
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
            english
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
    terms_text="""1. Introduction :
These Terms of Service govern your use of Ani-Me-Downloader. By accessing or using this application, you agree to be bound by these Terms and all applicable laws and regulations.
2. Purpose :
The core aim of Ani-Me-Downloader is to co-relate automation and efficiency to extract what is provided to a user on the internet. All content available through the application is hosted by external non-affiliated sources.
3. Content :
All content served through this application is publicly accessible. Ani-Me-Downloader has no control over the content it serves, and any use of copyrighted content from the providers is at the user's own risk.
4. User Conduct :
You agree to use Ani-Me-Downloader in a manner that is lawful, respectful, and in accordance with these Terms. You may not use this application in any way that could harm, disable, or impair this application or interfere with any other party's use and enjoyment of the application.
5. Disclaimer :
This project is to be used at the user's own risk, based on their government and laws. Any copyright infringements or DMCA in this project's regards are to be forwarded to the associated site by the associated notifier of any such claims.
6. Limitation of Liability :
In no event shall Ani-Me-Downloader or its developers be liable for any damages (including, without limitation, damages for loss of data or profit, or due to business interruption) arising out of the use or inability to use the materials on Ani-Me-Downloader's application, even if Ani-Me-Downloader or an authorized representative has been notified orally or in writing of the possibility of such damage.
"""
    about_text0="""
Welcome to Ani-Me-Downloader.
This application is made to help in your anime consumption.
It is still in development so you may face some bugs.
To use this application you REALLY need to follow the next steps.
Press okay to continue.
"""
    about_text1="""
You must have qbittorrent installed on your system to use this application.
Press okay to start downloading it in your browser.
"""
    about_text2="""
Open the downloaded file and follow the instructions to install qbittorrent.
After the application is Install on your system press okay to continue.
"""
    about_text="""Coming back to the tour :|
You can search for the things to download from the search tab.
then you can choose the the things from list of things that you searched for.
After that, you can verify all the info and click on okay to start.
And Voila! You're done. You can see the progress in the library tab.
"""