# recommender/auth.py
import os
from pathlib import Path
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_client(
    scopes,
    cache_path=".cache-web"
) -> spotipy.Spotify:

    load_dotenv(dotenv_path=Path(".env"))

    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=" ".join(scopes),
        cache_path=cache_path,
        open_browser=True,          # ✅ CLAVE
        show_dialog=True
    )

    return spotipy.Spotify(auth_manager=auth_manager)
