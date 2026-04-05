from pathlib import Path
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from datetime import date

# =========================
# Configuración
# =========================
CACHE_PATH = ".cache-playlist"
DEFAULT_PLAYLIST_PUBLIC = False

# =========================
# Auth
# =========================
def get_spotify_client():
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")

    cid   = os.getenv("SPOTIPY_CLIENT_ID")
    sec   = os.getenv("SPOTIPY_CLIENT_SECRET")
    redir = os.getenv("SPOTIPY_REDIRECT_URI")

    missing = [k for k, v in {
        "SPOTIPY_CLIENT_ID": cid,
        "SPOTIPY_CLIENT_SECRET": sec,
        "SPOTIPY_REDIRECT_URI": redir
    }.items() if not v]

    if missing:
        raise SystemExit(f"❌ Faltan variables en .env: {', '.join(missing)}")

    auth = SpotifyOAuth(
        client_id=cid,
        client_secret=sec,
        redirect_uri=redir,
        scope="playlist-modify-public playlist-modify-private",
        cache_path=CACHE_PATH,
        open_browser=True
    )

    return spotipy.Spotify(auth_manager=auth)

# =========================
# Playlist
# =========================
def create_playlist(
    sp: spotipy.Spotify,
    user_id: str,
    name: str,
    description: str,
    public: bool
) -> dict:
    return sp.user_playlist_create(
        user=user_id,
        name=name,
        public=public,
        description=description
    )

def add_tracks_to_playlist(
    sp: spotipy.Spotify,
    playlist_id: str,
    track_ids: list[str]
):
    uris = [f"spotify:track:{tid}" for tid in track_ids]
    sp.playlist_add_items(playlist_id, uris)

# =========================
# Main
# =========================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create Spotify playlist from CSV")
    parser.add_argument("--csv", required=True, help="recommendations_final.csv")
    parser.add_argument("--name", default=None, help="Nombre de la playlist")
    parser.add_argument("--public", action="store_true", help="Crear playlist pública")
    args = parser.parse_args()

    print("▶︎ Cargando CSV de recomendaciones …")
    df = pd.read_csv(args.csv)

    if df.empty:
        raise SystemExit("❌ El CSV está vacío")

    track_ids = df["track_id"].dropna().tolist()
    if not track_ids:
        raise SystemExit("❌ No hay track_ids en el CSV")

    sp = get_spotify_client()
    me = sp.me()
    user_id = me["id"]

    today = date.today().isoformat()
    playlist_name = args.name or f"Python Spotify Recommender by Marta · {today}"
    description = "Playlist generada automáticamente a partir de tu historial de escucha por el motor de recomendación de Marta hecho en Python. Incluye canciones nuevas que encajan con tu gusto, evitando artistas y temas que ya conoces, versiones repetidas y remixes"

    print(f"▶︎ Creando playlist: {playlist_name}")
    playlist = create_playlist(
        sp=sp,
        user_id=user_id,
        name=playlist_name,
        description=description,
        public=args.public
    )

    playlist_id = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]

    print("▶︎ Añadiendo tracks …")
    add_tracks_to_playlist(sp, playlist_id, track_ids)

    print("\n✅ Playlist creada con éxito")
    print(f"🔗 {playlist_url}")

if __name__ == "__main__":
    main()
