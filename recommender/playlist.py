# recommender/playlist.py
from datetime import date

PROJECT_NAME = "Python Spotify Recommender by Marta"

def create_playlist_from_tracks(sp, tracks, public=True):
    user_id = sp.me()["id"]

    playlist = sp.user_playlist_create(
        user=user_id,
        name=f"{PROJECT_NAME} · {date.today()}",
        public=public,
        description="Playlist generada automáticamente a partir de tu historial de escucha por el motor de recomendación de Marta hecho en Python. Incluye canciones nuevas que encajan con tu gusto, evitando artistas y temas que ya conoces, versiones repetidas y remixes"
    )

    track_ids = [t["track_id"] for t in tracks if t.get("track_id")]
    sp.playlist_add_items(playlist["id"], track_ids)

    return playlist
