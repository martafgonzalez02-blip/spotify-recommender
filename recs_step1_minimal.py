from pathlib import Path
import re, sys
import pandas as pd
import spotipy

from recommender.auth import get_spotify_client
from recommender.config import SCOPES_TOP_READ, CACHE_CLI

CSV_IN = "top_tracks_features.csv"
ID_RE  = re.compile(r"^[0-9A-Za-z]{22}$")  # IDs base62 de 22 chars

def load_spotify():
    return get_spotify_client(scopes=SCOPES_TOP_READ, cache_path=CACHE_CLI)

def clean_id(kind: str, raw):
    if raw is None: return None
    s = str(raw).strip()
    if ID_RE.match(s): return s
    if s.startswith("spotify:"):
        parts = s.split(":")
        if len(parts) >= 3 and parts[-2] in {"track","artist"} and ID_RE.match(parts[-1]):
            return parts[-1]
    if "open.spotify.com" in s:
        seg = s.split("?")[0].rstrip("/").split("/")[-1]
        if ID_RE.match(seg): return seg
    return None

def take_valid_ids(kind: str, values, max_n):
    out, bad = [], []
    for v in values:
        vid = clean_id(kind, v)
        if vid:
            out.append(vid)
        else:
            bad.append(v)
        if len(out) >= max_n: break
    return out, bad

def main():
    # 1) Leer CSV y validar columnas
    if not Path(CSV_IN).exists():
        print(f"❌ No existe {CSV_IN}")
        sys.exit(1)
    df = pd.read_csv(CSV_IN)
    for col in ("track_id","artist_id"):
        if col not in df.columns:
            print(f"❌ Falta columna '{col}' en {CSV_IN}")
            sys.exit(1)
    print(f"✅ CSV cargado: {len(df)} filas")

    # 2) Extraer semillas y mostrar inválidas
    seed_artists, bad_art = take_valid_ids("artist", df["artist_id"].tolist(), max_n=2)
    seed_tracks,  bad_trk = take_valid_ids("track",  df["track_id"].tolist(),  max_n=3)

    print(f"Semillas artistas: {seed_artists}")
    print(f"Semillas tracks  : {seed_tracks}")

    if bad_art:
        print(f"⚠️ {len(bad_art)} artist_id inválidos (mostrando 3): {bad_art[:3]}")
    if bad_trk:
        print(f"⚠️ {len(bad_trk)} track_id inválidos (mostrando 3): {bad_trk[:3]}")

    if not seed_artists and not seed_tracks:
        print("❌ No hay semillas válidas. Revisa el CSV.")
        sys.exit(1)

    # 3) Auth y llamada mínima a /recommendations (listas, NO strings)
    sp = load_spotify()

    me = sp.me()
    market = me.get("country")
    print(f"👤 {me['display_name']} · market={market}")

    # Fallback si Spotify no te da country (perfiles sin país)
    if not market:
        market = "ES"  # o el que prefieras: "US", "GB", etc.

    try:
        # NO pases market si está vacío; pásalo solo si hay valor
        rec_kwargs = {
            "seed_artists": seed_artists if seed_artists else None,
            "seed_tracks": seed_tracks if seed_tracks else None,
            "limit": 20,
        }
        if market:
            rec_kwargs["market"] = market

        recs = sp.recommendations(**rec_kwargs)["tracks"]
    except spotipy.SpotifyException as e:
        # Si fuera un 401, reautenticamos borrando solo la caché de lectura
        if getattr(e, "http_status", None) == 401:
            Path(CACHE_CLI).unlink(missing_ok=True)
            sp = load_spotify()
            recs = sp.recommendations(**rec_kwargs)["tracks"]
        else:
            raise
