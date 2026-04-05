from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd

from recommender.auth import get_spotify_client
from recommender.recommendations import generate_recommendations
from recommender.playlist import create_playlist_from_tracks

# =========================
# Configuración global
# =========================

SPOTIFY_SCOPES = [
    "user-top-read",
    "playlist-modify-public",
    "playlist-modify-private",
]

CACHE_WEB = ".cache-web"

# =========================
# App
# =========================

app = FastAPI(title="Python Spotify Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# =========================
# Helpers
# =========================

def is_logged_in():
    try:
        sp = get_spotify_client(
            scopes=SPOTIFY_SCOPES,
            cache_path=CACHE_WEB
        )
        sp.me()
        return True
    except:
        return False


def get_spotify():
    return get_spotify_client(
        scopes=SPOTIFY_SCOPES,
        cache_path=CACHE_WEB
    )

# =========================
# Routes
# =========================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"logged": is_logged_in()}
    )


@app.get("/login")
def login():
    sp = get_spotify()
    auth_url = sp.auth_manager.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback")
def callback(code: str):
    print("✅ CALLBACK EJECUTADO")
    sp = get_spotify()
    sp.auth_manager.get_access_token(code)
    return RedirectResponse("/")


@app.post("/playlist")
def create_playlist(public: bool = True):

    # 🔐 Asegurar login
    try:
        sp = get_spotify()
        sp.me()
    except:
        return RedirectResponse("/login")

    # 1️⃣ Top tracks
    top = sp.current_user_top_tracks(
        limit=50,
        time_range="medium_term"
    )["items"]

    if not top:
        return {"error": "No hay suficiente histórico"}

    artist_ids = [t["artists"][0]["id"] for t in top]

    # 2️⃣ Géneros reales
    artists_info = sp.artists(list(set(artist_ids)))["artists"]
    artist_genres = {
        a["id"]: ", ".join(a.get("genres", []))
        for a in artists_info
    }

    rows = []
    for t in top:
        rows.append({
            "track_id": t["id"],
            "artist_id": t["artists"][0]["id"],
            "genres": artist_genres.get(t["artists"][0]["id"], "")
        })

    df = pd.DataFrame(rows)

    # 3️⃣ Motor de recomendaciones
    recs = generate_recommendations(
        sp=sp,
        top_df=df,
        discovery=True,
        size=15
    )

    if not recs:
        return {"error": "No se pudieron generar recomendaciones"}

    # 4️⃣ Crear playlist
    playlist = create_playlist_from_tracks(
        sp=sp,
        tracks=recs,
        public=public
    )

    return {
        "playlist_name": playlist["name"],
        "playlist_url": playlist["external_urls"]["spotify"],
        "tracks": len(recs)
    }
