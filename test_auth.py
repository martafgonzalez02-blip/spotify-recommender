from pathlib import Path
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# 1) Cargar .env desde la carpeta del script (no depender del CWD)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

CID   = os.getenv("SPOTIPY_CLIENT_ID")
SECRET= os.getenv("SPOTIPY_CLIENT_SECRET")
REDIR = os.getenv("SPOTIPY_REDIRECT_URI")

missing = [k for k,v in {
    "SPOTIPY_CLIENT_ID": CID,
    "SPOTIPY_CLIENT_SECRET": SECRET,
    "SPOTIPY_REDIRECT_URI": REDIR
}.items() if not v]
if missing:
    raise SystemExit(f"❌ Faltan variables en .env: {', '.join(missing)}")

# 2) Construir el auth manager explícitamente
auth = SpotifyOAuth(
    client_id=CID,
    client_secret=SECRET,
    redirect_uri=REDIR,
    scope="user-top-read",
    cache_path=".cache-debug",   # cache separado para esta prueba
    open_browser=True
)

# 3) Forzar obtención del token antes de crear el cliente
token_info = auth.get_access_token(as_dict=True)
if not token_info or "access_token" not in token_info:
    raise SystemExit("❌ No se pudo obtener token. Revisa redirect_uri y el login en el navegador.")

print("✅ Token obtenido.")
print(f"   scope: {token_info.get('scope')}")
print(f"   expira en: {token_info.get('expires_in')} s")
print("   Access Token:")
print(token_info["access_token"]) 

# 4) Crear cliente con auth correcto y probar /me
sp = spotipy.Spotify(auth_manager=auth)
me = sp.me()
print(f"✅ Autenticado como: {me['display_name']} ({me['id']})")
