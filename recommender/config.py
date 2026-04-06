# recommender/config.py
# Punto único de configuración: credenciales, scopes, cachés y constantes.
from pathlib import Path
import os
from dotenv import load_dotenv

# Ruta robusta al .env independientemente del directorio de trabajo
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# --- Credenciales Spotify ---
SPOTIPY_CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI  = os.getenv("SPOTIPY_REDIRECT_URI")

_missing = [k for k, v in {
    "SPOTIPY_CLIENT_ID":     SPOTIPY_CLIENT_ID,
    "SPOTIPY_CLIENT_SECRET": SPOTIPY_CLIENT_SECRET,
    "SPOTIPY_REDIRECT_URI":  SPOTIPY_REDIRECT_URI,
}.items() if not v]
if _missing:
    raise SystemExit(f"❌ Faltan variables en .env: {', '.join(_missing)}")

# --- Scopes OAuth ---
SCOPES_TOP_READ = ["user-top-read"]
SCOPES_PLAYLIST = ["playlist-modify-public", "playlist-modify-private"]
SCOPES_WEB      = SCOPES_TOP_READ + SCOPES_PLAYLIST

# --- Cachés OAuth ---
CACHE_WEB      = ".cache-web"
CACHE_PLAYLIST = ".cache-playlist"
CACHE_FEATURES = ".cache-features"
CACHE_READ     = ".cache-read"

# --- Constantes de proyecto ---
PROJECT_NAME         = "Python Spotify Recommender by Marta"
PLAYLIST_DESCRIPTION = (
    "Playlist generada automáticamente a partir de tu historial de escucha "
    "por el motor de recomendación de Marta hecho en Python. Incluye canciones "
    "nuevas que encajan con tu gusto, evitando artistas y temas que ya conoces, "
    "versiones repetidas y remixes"
)
