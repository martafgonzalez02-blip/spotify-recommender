# top_tracks_features.py
from pathlib import Path
import os
import time
from typing import List, Dict
import pandas as pd
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from requests.exceptions import HTTPError

# -------- Config --------
FEATURE_KEYS = [
    "danceability", "energy", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo"
]
DEFAULT_TIME_RANGE = "medium_term"  # short_term | medium_term | long_term
TOP_LIMIT = 50
CACHE_PATH = ".cache-features"      # cache propio para este script

# -------- Utils --------
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def get_spotify_client(scopes: List[str]) -> spotipy.Spotify:
    """Auth explícita desde .env y cache propio."""
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    cid   = os.getenv("SPOTIPY_CLIENT_ID")
    sec   = os.getenv("SPOTIPY_CLIENT_SECRET")
    redir = os.getenv("SPOTIPY_REDIRECT_URI")
    missing = [k for k, v in {
        "SPOTIPY_CLIENT_ID": cid, "SPOTIPY_CLIENT_SECRET": sec, "SPOTIPY_REDIRECT_URI": redir
    }.items() if not v]
    if missing:
        raise SystemExit(f"❌ Faltan variables en .env: {', '.join(missing)}")

    auth = SpotifyOAuth(
        client_id=cid,
        client_secret=sec,
        redirect_uri=redir,
        scope=" ".join(scopes),
        cache_path=CACHE_PATH,
        open_browser=True
    )
    return spotipy.Spotify(auth_manager=auth)

# -------- Fetchers --------
def fetch_top_tracks(sp: spotipy.Spotify, time_range=DEFAULT_TIME_RANGE, limit=TOP_LIMIT):
    res = sp.current_user_top_tracks(time_range=time_range, limit=min(limit, 50))
    return res.get("items", [])

def fetch_audio_features(sp: spotipy.Spotify, track_ids: List[str]) -> Dict[str, dict]:
    """Batch seguro (<=90) + fallback uno-a-uno si falla el batch."""
    out: Dict[str, dict] = {}
    for batch in chunks(track_ids, 90):
        try:
            feats = sp.audio_features(batch)
            for f in feats or []:
                if f and f.get("id"):
                    out[f["id"]] = f
        except (spotipy.SpotifyException, HTTPError) as e:
            print(f"⚠️ Error batch audio_features ({len(batch)} ids). Fallback 1x1. Detalle: {e}")
            for tid in batch:
                try:
                    f = sp.audio_features([tid])[0]
                    if f and f.get("id"):
                        out[f["id"]] = f
                    time.sleep(0.05)
                except Exception as ee:
                    print(f"   – fallo con {tid}: {ee}")
    return out

def fetch_artists_genres(sp: spotipy.Spotify, artist_ids: List[str]) -> Dict[str, List[str]]:
    genres: Dict[str, List[str]] = {}
    unique = [a for a in dict.fromkeys(artist_ids) if a]
    for batch in chunks(unique, 50):
        arts = sp.artists(batch)["artists"]
        for a in arts:
            genres[a["id"]] = a.get("genres", []) or []
    return genres

# -------- Transform --------
def build_dataframe(top_tracks: List[dict], features_map: Dict[str, dict], artist_genres: Dict[str, List[str]]) -> pd.DataFrame:
    rows = []
    for t in top_tracks:
        tid = t.get("id")
        if not tid:
            continue
        f = features_map.get(tid, {}) or {}
        primary = (t.get("artists") or [None])[0]
        a_id = primary.get("id") if primary else None
        genres = artist_genres.get(a_id, []) if a_id else []
        rows.append({
            "track_name": t.get("name"),
            "artist_name": primary.get("name") if primary else None,
            "album": (t.get("album") or {}).get("name"),
            "release_date": (t.get("album") or {}).get("release_date"),
            "popularity": t.get("popularity"),
            "genres": ", ".join(genres[:5]),
            "track_id": tid,
            "artist_id": a_id,
            **{k: f.get(k) for k in FEATURE_KEYS}
        })
    cols = ["track_name", "artist_name", "album", "release_date", "popularity",
            "genres", "track_id", "artist_id"] + FEATURE_KEYS
    return pd.DataFrame(rows, columns=cols)

def summarize_profile(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    summary = df[FEATURE_KEYS].median(numeric_only=True).round(2)
    if "tempo" in summary and pd.notna(summary["tempo"]):
        summary["tempo"] = int(summary["tempo"])
    return summary

# -------- Main --------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Top Tracks + Audio Features + Perfil Sonoro")
    parser.add_argument("--time-range", choices=["short_term", "medium_term", "long_term"],
                        default=DEFAULT_TIME_RANGE, help="short_term (4 semanas), medium_term (6 meses), long_term (años)")
    parser.add_argument("--limit", type=int, default=TOP_LIMIT, help="Nº de top tracks (máx 50)")
    parser.add_argument("--out", default="top_tracks_features.csv", help="CSV de salida")
    args = parser.parse_args()

    sp = get_spotify_client(scopes=["user-top-read"])

    print("▶︎ Descargando Top Tracks…")
    top = fetch_top_tracks(sp, time_range=args.time_range, limit=args.limit)
    if not top:
        raise SystemExit("⚠️ No hay Top Tracks. Escucha música y vuelve a intentarlo.")

    track_ids = [t["id"] for t in top if t.get("id")]
    artist_ids = [t["artists"][0]["id"] for t in top if t.get("artists")]

    print("▶︎ Descargando Audio Features…")
    feats = fetch_audio_features(sp, track_ids)

    valid_feats = [f for f in feats.values() if f]
    print(f"🎛 Audio features válidas: {len(valid_feats)} / {len(track_ids)}")


    print("▶︎ Descargando géneros (artista principal)…")
    genres = fetch_artists_genres(sp, artist_ids)

    print("▶︎ Construyendo dataset…")
    df = build_dataframe(top, feats, genres)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"✅ CSV guardado → {args.out}  ({len(df)} filas)")

    print("\n🎛  Perfil sonoro (medianas):")
    summary = summarize_profile(df)
    if not summary.empty:
        for k, v in summary.items():
            print(f"  - {k}: {v}")
    else:
        print("  (sin datos)")

    print("\n👥 Artistas más frecuentes:")
    print(df["artist_name"].value_counts().head(10).to_string())

    print("\n🧪 Muestra (primeras 8 filas):")
    with pd.option_context("display.max_columns", None):
        print(df.head(8).to_string(index=False))

if __name__ == "__main__":
    main()

