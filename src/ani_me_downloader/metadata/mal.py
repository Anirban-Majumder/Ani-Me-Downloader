# coding: utf-8
"""MyAnimeList OAuth (PKCE public client) + read/write of list status."""
import json
import os
import secrets
import urllib.parse as urlparse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

CLIENT_ID = "e6982f4701756335e43de16978a25a7c"
CLIENT_SECRET = ""
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".Ani-Me-Downloader", "mal_token.json")


def get_new_code_verifier() -> str:
    return secrets.token_urlsafe(100)[:128]


class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(parsed_path.query)
        if "code" in query:
            self.server.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization Successful!</h1>")
            self.wfile.write(b"<p>You can close this window and return to the application.</p></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing 'code' parameter.")


def run_server(port: int = 5000) -> str:
    httpd = HTTPServer(("", port), OAuthHandler)
    print(f"Starting local server on port {port} to capture OAuth code...")
    httpd.handle_request()
    return httpd.auth_code


def authorize_mal() -> dict:
    code_verifier = code_challenge = get_new_code_verifier()
    auth_url = (
        f"https://myanimelist.net/v1/oauth2/authorize?response_type=code"
        f"&client_id={CLIENT_ID}&code_challenge={code_challenge}"
    )
    print("Opening browser for MAL authorization...")
    webbrowser.open(auth_url)
    auth_code = run_server()
    return exchange_code_for_token(auth_code, code_verifier)


def exchange_code_for_token(authorization_code: str, code_verifier: str) -> dict:
    response = requests.post(
        "https://myanimelist.net/v1/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": authorization_code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    token = response.json()
    save_token(token)
    print("Token generated successfully!")
    return token


def save_token(token: dict) -> None:
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=4)
        print(f'Token saved in "{TOKEN_FILE}"')


def load_token() -> dict | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def refresh_token(refresh_token_str: str) -> dict:
    response = requests.post(
        "https://myanimelist.net/v1/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token_str,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    token = response.json()
    save_token(token)
    print("Token refreshed successfully!")
    return token


def make_authenticated_request(url, method="GET", params=None, data=None):
    """Authenticated MAL request with auto-refresh on 401."""
    token_data = load_token() or authorize_mal()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    if method.upper() == "GET":
        response = requests.get(url, headers=headers, params=params)
    elif method.upper() == "PUT":
        # PUT uses form data; pass `params` as the body.
        response = requests.put(url, headers=headers, data=params)
    else:
        raise ValueError(f"Unsupported method: {method}")

    if response.status_code == 401:
        print("Access token expired, refreshing...")
        if "refresh_token" in token_data:
            token_data = refresh_token(token_data["refresh_token"])
        else:
            print("No refresh token available, need to re-authorize")
            token_data = authorize_mal()
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, data=params)

    response.raise_for_status()
    return response


def get_anime_details(anime_id, fields=None):
    """Public-fields fallback when no token; otherwise hit OAuth path."""
    if fields is None:
        fields = (
            "synopsis,mean,rank,popularity,num_episodes,start_date,end_date,"
            "genres,studios,main_picture,media_type,status,my_list_status"
        )
    url = f"https://api.myanimelist.net/v2/anime/{anime_id}"
    params = {"fields": fields}

    token_data = load_token()
    if token_data and "access_token" in token_data:
        response = make_authenticated_request(url, method="GET", params=params)
    else:
        headers = {"X-MAL-CLIENT-ID": CLIENT_ID}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

    return response.json()


def update_anime_status(anime_id, status=None, score=None, num_watched_episodes=None):
    """Update a MAL list entry."""
    url = f"https://api.myanimelist.net/v2/anime/{anime_id}/my_list_status"
    params: dict = {}
    if status is not None:
        params["status"] = status
    if score is not None:
        params["score"] = score
    if num_watched_episodes is not None:
        params["num_watched_episodes"] = num_watched_episodes

    response = make_authenticated_request(url, method="PUT", params=params)
    print(response.text)
    if response.status_code == 200:
        print(f"Successfully updated anime (ID: {anime_id})")
        return True
    print(f"Failed to update anime: {response.status_code} - {response.text}")
    return False
