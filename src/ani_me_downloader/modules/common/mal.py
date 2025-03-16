import requests
import webbrowser
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse

# Constants
CLIENT_ID = 'e6982f4701756335e43de16978a25a7c'
CLIENT_SECRET = ''
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".Ani-Me-Downloader", "mal_token.json")


def get_new_code_verifier() -> str:
    """Generate a new Code Verifier for PKCE OAuth flow"""
    token = secrets.token_urlsafe(100)
    return token[:128]

class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence server logs
        return
        
    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        query_components = urlparse.parse_qs(parsed_path.query)
        if 'code' in query_components:
            self.server.auth_code = query_components['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization Successful!</h1>")
            self.wfile.write(b"<p>You can close this window and return to the application.</p></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing 'code' parameter.")

def run_server(port=5000):
    """Run a local HTTP server to capture the OAuth callback"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, OAuthHandler)
    print(f"Starting local server on port {port} to capture OAuth code...")
    httpd.handle_request()  # handles a single request then returns
    return httpd.auth_code

def authorize_mal():
    """Initiate MAL authorization flow and save token"""
    code_verifier = code_challenge = get_new_code_verifier()
    
    auth_url = (
        f"https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&code_challenge={code_challenge}"
    )
    print("Opening browser for MAL authorization...")
    webbrowser.open(auth_url)
    
    auth_code = run_server()
    token_data = exchange_code_for_token(auth_code, code_verifier)
    
    return token_data

def exchange_code_for_token(authorization_code: str, code_verifier: str) -> dict:
    """Exchange authorization code for access token"""
    url = 'https://myanimelist.net/v1/oauth2/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': authorization_code,
        'code_verifier': code_verifier,
        'grant_type': 'authorization_code'
    }

    response = requests.post(url, data)
    response.raise_for_status()

    token = response.json()
    save_token(token)
    print('Token generated successfully!')
    
    return token

def save_token(token: dict):
    """Save token data to file"""
    with open(TOKEN_FILE, 'w') as file:
        json.dump(token, file, indent=4)
        print(f'Token saved in "{TOKEN_FILE}"')

def load_token() -> dict:
    """Load token data from file"""
    if not os.path.exists(TOKEN_FILE):
        return None
    
    with open(TOKEN_FILE, 'r') as file:
        return json.load(file)

def refresh_token(refresh_token_str: str) -> dict:
    """Get a new access token using a refresh token"""
    url = 'https://myanimelist.net/v1/oauth2/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token_str,
        'grant_type': 'refresh_token'
    }

    response = requests.post(url, data)
    response.raise_for_status()

    token = response.json()
    save_token(token)
    print('Token refreshed successfully!')
    
    return token

def make_authenticated_request(url, method='GET', params=None, data=None):
    """
    Make an authenticated request to MAL API with automatic token refresh
    when expired
    """
    token_data = load_token()
    
    # If no token exists, start authorization flow
    if not token_data:
        token_data = authorize_mal()
    
    access_token = token_data['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Make the request - important change: use data for PUT requests
    if method.upper() == 'GET':
        response = requests.get(url, headers=headers, params=params)
    elif method.upper() == 'PUT':
        # Use data parameter for PUT requests (form data), not params
        response = requests.put(url, headers=headers, data=params)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    # If token expired (401), refresh and retry
    if response.status_code == 401:
        print("Access token expired, refreshing...")
        if 'refresh_token' in token_data:
            token_data = refresh_token(token_data['refresh_token'])
            access_token = token_data['access_token']
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Retry with new token - apply the same fix here
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, data=params)
        else:
            # No refresh token, need to re-authorize
            print("No refresh token available, need to re-authorize")
            token_data = authorize_mal()
            access_token = token_data['access_token']
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Retry with new token - apply the same fix here too
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, data=params)
    
    response.raise_for_status()
    return response

def update_anime_status(anime_id, status=None, score=None, num_watched_episodes=None):
    """
    Update anime entry in MyAnimeList
    
    Args:
        anime_id: MAL anime ID
        status: 'watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch'
        score: Rating (1-10)
        num_watched_episodes: Number of episodes watched
    
    Returns:
        True if successful
    """
    url = f'https://api.myanimelist.net/v2/anime/{anime_id}/my_list_status'
    
    # Only include parameters that are provided
    params = {}
    if status is not None:
        params['status'] = status
    if score is not None:
        params['score'] = score
    if num_watched_episodes is not None:
        # Fix: The parameter name in the MyAnimeList API is 'num_watched_episodes'
        params['num_watched_episodes'] = num_watched_episodes
    
    response = make_authenticated_request(url, method='PUT', params=params)
    print(response.text)
    if response.status_code == 200:
        print(f"Successfully updated anime (ID: {anime_id})")
        return True
    else:
        print(f"Failed to update anime: {response.status_code} - {response.text}")
        return False
    


# Command-line auth flow
if __name__ == "__main__":
    update_anime_status(
        anime_id=58502,  # Example Mal ID
        status="watching",
        score=8,
        num_watched_episodes=5
    )