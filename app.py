from flask import Flask, render_template, redirect, request, jsonify
import pandas as pd

from recommender.auth import get_spotify_client
from recommender.recommendations import generate_recommendations
from recommender.playlist import create_playlist_from_tracks
from recommender.config import SCOPES_WEB, CACHE_WEB

# =========================
# App
# =========================
app = Flask(__name__)


# =========================
# Helpers
# =========================
def is_logged_in():
    try:
        sp = get_spotify_client(scopes=SCOPES_WEB, cache_path=CACHE_WEB)
        sp.me()
        return True
    except:
        return False


def get_spotify():
    return get_spotify_client(scopes=SCOPES_WEB, cache_path=CACHE_WEB)


# =========================
# Routes
# =========================
@app.route("/")
def index():
    return render_template("index.html", logged=is_logged_in())


@app.route("/login")
def login():
    sp = get_spotify()
    auth_url = sp.auth_manager.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return f"Error en autenticación: {error}", 400

    if not code:
        return "No se recibió código de autorización", 400

    print("✅ CALLBACK EJECUTADO")
    sp = get_spotify()
    sp.auth_manager.get_access_token(code)
    return redirect("/")


@app.route("/playlist", methods=["POST"])
def create_playlist():
    public = request.args.get("public", "true").lower() == "true"

    # 🔐 Asegurar login
    try:
        sp = get_spotify()
        sp.me()
    except:
        return redirect("/login")

    # 1️⃣ Top tracks
    top = sp.current_user_top_tracks(
        limit=50,
        time_range="medium_term"
    )["items"]

    if not top:
        return jsonify({"error": "No hay suficiente histórico"})

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
        return jsonify({"error": "No se pudieron generar recomendaciones"})

    # 4️⃣ Crear playlist
    playlist = create_playlist_from_tracks(
        sp=sp,
        tracks=recs,
        public=public
    )

    return jsonify({
        "playlist_name": playlist["name"],
        "playlist_url": playlist["external_urls"]["spotify"],
        "tracks": len(recs)
    })


# =========================
# Local development
# =========================
if __name__ == "__main__":
    app.run(debug=True, port=8000)