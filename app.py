from flask import Flask, render_template, redirect, request, jsonify, session
import pandas as pd
import os
import uuid

from recommender.auth import get_spotify_client
from recommender.recommendations import generate_recommendations
from recommender.playlist import create_playlist_from_tracks
from recommender.config import SCOPES_WEB

app = Flask(__name__)

# Clave secreta para firmar las cookies de sesión
app.secret_key = os.getenv("FLASK_SECRET_KEY", "cambia-esto-en-produccion")

# Carpeta donde guardar los caches por usuario
CACHE_FOLDER = os.path.join(os.path.dirname(__file__), ".spotify_caches")
os.makedirs(CACHE_FOLDER, exist_ok=True)


def get_user_cache_path():
    """Devuelve la ruta del cache del usuario actual (basado en su sesión)."""
    if "uuid" not in session:
        session["uuid"] = str(uuid.uuid4())
    return os.path.join(CACHE_FOLDER, f".cache-{session['uuid']}")


def is_logged_in():
    try:
        sp = get_spotify_client(scopes=SCOPES_WEB, cache_path=get_user_cache_path())
        sp.me()
        return True
    except:
        return False


def get_spotify():
    return get_spotify_client(scopes=SCOPES_WEB, cache_path=get_user_cache_path())


@app.route("/")
def index():
    return render_template("index.html", logged=is_logged_in())


@app.route("/login")
def login():
    # Forzar nuevo login: borrar cache anterior si existe
    cache_path = get_user_cache_path()
    if os.path.exists(cache_path):
        os.remove(cache_path)
    
    sp = get_spotify()
    auth_url = sp.auth_manager.get_authorize_url()
    return redirect(auth_url)


@app.route("/logout")
def logout():
    """Cerrar sesión: borra el cache del usuario y limpia su session."""
    cache_path = get_user_cache_path()
    if os.path.exists(cache_path):
        os.remove(cache_path)
    session.clear()
    return redirect("/")


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

    try:
        sp = get_spotify()
        sp.me()
    except:
        return redirect("/login")

    top = sp.current_user_top_tracks(
        limit=50,
        time_range="medium_term"
    )["items"]

    if not top:
        return jsonify({"error": "No hay suficiente histórico"})

    artist_ids = [t["artists"][0]["id"] for t in top]
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

    recs = generate_recommendations(
        sp=sp,
        top_df=df,
        discovery=True,
        size=15
    )

    if not recs:
        return jsonify({"error": "No se pudieron generar recomendaciones"})

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


if __name__ == "__main__":
    app.run(debug=True, port=8000)