# recommender/auth.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, CACHE_WEB

def get_spotify_client(scopes, cache_path=CACHE_WEB) -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=" ".join(scopes),
        cache_path=cache_path,
        open_browser=True,
        show_dialog=True
    )
    return spotipy.Spotify(auth_manager=auth_manager)
