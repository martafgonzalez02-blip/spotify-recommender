import re
import random
from typing import List, Optional
import pandas as pd
from spotipy.exceptions import SpotifyException

# =========================
# Configuración
# =========================
POPULARITY_DISCOVERY = (20, 60)

BAD_KEYWORDS = [
    "version", "remaster", "live", "en directo",
    "karaoke", "tribute", "cover", "instrumental"
]

REMIX_KEYWORDS = [
    "remix", "edit", "rework", "extended",
    "club mix", "radio edit"
]

# =========================
# Utilidades
# =========================
def normalize_track_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(
        r"\s*-\s*(remix|edit|rework|version|radio edit|live|extended).*",
        "",
        name
    )
    name = re.sub(r"\s+", " ", name).strip()
    return name


def dedupe_by_track_name(tracks: List[dict]) -> List[dict]:
    seen = set()
    result = []
    for t in tracks:
        norm = normalize_track_name(t.get("name", ""))
        if norm and norm not in seen:
            seen.add(norm)
            result.append(t)
    return result


def apply_variation(
    tracks: List[dict],
    size: int,
    sample_ratio: float = 0.6
) -> List[dict]:
    if not tracks:
        return tracks

    shuffled = tracks[:]
    random.shuffle(shuffled)

    k = max(size * 2, int(len(shuffled) * sample_ratio))
    return shuffled[:k]


# =========================
# Contexto usuario
# =========================
def pick_seed_artists(df: pd.DataFrame, k: int = 2) -> set:
    return set(
        df["artist_id"]
        .value_counts()
        .head(k)
        .index
        .tolist()
    )


def pick_top_artists(df: pd.DataFrame) -> set:
    return set(df["artist_id"].dropna().tolist())


def extract_genres(df: pd.DataFrame, max_genres: int = 5) -> List[str]:
    genres = []
    for g in df.get("genres", []).dropna():
        genres.extend([x.strip() for x in g.split(",") if x.strip()])
    return list(dict.fromkeys(genres))[:max_genres]


# =========================
# Universo de artistas
# =========================
def fetch_related_artists(sp, artist_ids: List[str]) -> List[dict]:
    related = []
    for aid in artist_ids:
        try:
            res = sp.artist_related_artists(aid)
            related.extend(res.get("artists", []))
        except SpotifyException as e:
            if e.http_status != 404:
                raise
    return related


def search_artists_by_genre(
    sp,
    genres: List[str],
    limit_per_genre: int = 12
) -> List[dict]:
    artists = []
    for g in genres:
        q = f'genre:"{g}"'
        res = sp.search(q=q, type="artist", limit=limit_per_genre)
        artists.extend(res.get("artists", {}).get("items", []))
    return artists


# =========================
# Tracks candidatos
# =========================
def fetch_top_tracks_from_artists(
    sp,
    artists: List[dict],
    market: str
) -> List[dict]:
    tracks = []
    for a in artists:
        try:
            res = sp.artist_top_tracks(a["id"], country=market)
            tracks.extend(res.get("tracks", []))
        except SpotifyException as e:
            if e.http_status != 404:
                raise
    return tracks


# =========================
# Filtros
# =========================
def filter_known_tracks(tracks: List[dict], known_ids: set) -> List[dict]:
    return [t for t in tracks if t.get("id") and t["id"] not in known_ids]


def filter_versions(tracks: List[dict]) -> List[dict]:
    out = []
    for t in tracks:
        name = (t.get("name") or "").lower()
        if any(bad in name for bad in BAD_KEYWORDS):
            continue
        out.append(t)
    return out


def filter_seed_and_top_artists(
    tracks: List[dict],
    seed_artists: set,
    top_artists: set
) -> List[dict]:
    out = []
    for t in tracks:
        aid = t["artists"][0]["id"]
        if aid in seed_artists or aid in top_artists:
            continue
        out.append(t)
    return out


def filter_by_popularity(tracks: List[dict], band: tuple) -> List[dict]:
    lo, hi = band
    return [
        t for t in tracks
        if t.get("popularity") is not None and lo <= t["popularity"] <= hi
    ]


def remix_penalty_sort(tracks: List[dict]) -> List[dict]:
    def score(t):
        name = (t.get("name") or "").lower()
        penalty = 100 if any(r in name for r in REMIX_KEYWORDS) else 0
        pop = t.get("popularity") or 0
        return penalty - pop  # menor es mejor
    return sorted(tracks, key=score)


def diversify_by_artist(
    tracks: List[dict],
    size: int,
    max_per_artist: int = 1
) -> List[dict]:
    result, counts = [], {}
    for t in tracks:
        aid = t["artists"][0]["id"]
        if counts.get(aid, 0) < max_per_artist:
            result.append(t)
            counts[aid] = counts.get(aid, 0) + 1
        if len(result) >= size:
            break
    return result


# =========================
# Normalización de salida
# =========================
def track_to_public_dict(t: dict) -> dict:
    artist = t["artists"][0]
    return {
        "track_id": t["id"],
        "track_name": t["name"],
        "artist_name": artist["name"],
        "artist_id": artist["id"],
        "album": t["album"]["name"],
        "release_date": t["album"].get("release_date"),
        "popularity": t.get("popularity"),
        "reason": "descubrimiento compatible con tu perfil"
    }


# =========================
# API PRINCIPAL
# =========================
def generate_recommendations(
    sp,
    top_df: pd.DataFrame,
    discovery: bool = True,
    size: int = 15,
    seed: Optional[int] = None
) -> List[dict]:
    """
    Genera recomendaciones Spotify a partir del perfil del usuario.
    Devuelve lista de tracks normalizados (dicts).
    """

    if seed is not None:
        random.seed(seed)

    market = sp.me().get("country", "ES")

    seed_artists = pick_seed_artists(top_df)
    top_artists = pick_top_artists(top_df)
    known_ids = set(top_df["track_id"].dropna())

    related = fetch_related_artists(sp, list(seed_artists))

    if related:
        candidate_artists = related
    else:
        genres = extract_genres(top_df)
        candidate_artists = search_artists_by_genre(sp, genres)

    # Deduplicar artistas
    seen = set()
    artists = []
    for a in candidate_artists:
        if a["id"] not in seen:
            artists.append(a)
            seen.add(a["id"])

    tracks = fetch_top_tracks_from_artists(sp, artists, market)

    # Pipeline discovery
    base = filter_known_tracks(tracks, known_ids)
    base = filter_versions(base)
    base = filter_seed_and_top_artists(base, seed_artists, top_artists)
    base = dedupe_by_track_name(base)
    base = apply_variation(base, size=size, sample_ratio=0.6)
    base = remix_penalty_sort(base)

    pop = filter_by_popularity(base, POPULARITY_DISCOVERY)
    final = diversify_by_artist(pop, size=size, max_per_artist=1)

    if len(final) < size:
        final = diversify_by_artist(base, size=size, max_per_artist=1)

    # 🔒 Contrato estable de salida
    return [track_to_public_dict(t) for t in final[:size]]
