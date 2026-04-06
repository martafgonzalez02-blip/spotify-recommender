from pathlib import Path
import pandas as pd
from datetime import date

from recommender.auth import get_spotify_client
from recommender.config import SCOPES_PLAYLIST, CACHE_CLI

# =========================
# Playlist
# =========================
def create_playlist(sp, user_id, name, description, public) -> dict:
    return sp.user_playlist_create(
        user=user_id,
        name=name,
        public=public,
        description=description
    )

def add_tracks_to_playlist(sp, playlist_id, track_ids):
    uris = [f"spotify:track:{tid}" for tid in track_ids]
    sp.playlist_add_items(playlist_id, uris)

# =========================
# Main
# =========================
def main():
    import argparse
    from recommender.config import PROJECT_NAME, PLAYLIST_DESCRIPTION

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

    sp = get_spotify_client(scopes=SCOPES_PLAYLIST, cache_path=CACHE_CLI)
    me = sp.me()
    user_id = me["id"]

    today = date.today().isoformat()
    playlist_name = args.name or f"{PROJECT_NAME} · {today}"

    print(f"▶︎ Creando playlist: {playlist_name}")
    playlist = create_playlist(
        sp=sp,
        user_id=user_id,
        name=playlist_name,
        description=PLAYLIST_DESCRIPTION,
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
