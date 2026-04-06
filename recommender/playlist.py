# recommender/playlist.py
from datetime import date
from .config import PROJECT_NAME, PLAYLIST_DESCRIPTION

def create_playlist_from_tracks(sp, tracks, public=True):
    user_id = sp.me()["id"]

    playlist = sp.user_playlist_create(
        user=user_id,
        name=f"{PROJECT_NAME} · {date.today()}",
        public=public,
        description=PLAYLIST_DESCRIPTION
    )

    track_ids = [t["track_id"] for t in tracks if t.get("track_id")]
    sp.playlist_add_items(playlist["id"], track_ids)

    return playlist
