from recommender.auth import get_spotify_client
from recommender.config import SCOPES_TOP_READ, CACHE_CLI

auth_manager = get_spotify_client(scopes=SCOPES_TOP_READ, cache_path=CACHE_CLI).auth_manager

token_info = auth_manager.get_access_token(as_dict=True)
if not token_info or "access_token" not in token_info:
    raise SystemExit("❌ No se pudo obtener token. Revisa redirect_uri y el login en el navegador.")

print("✅ Token obtenido.")
print(f"   scope: {token_info.get('scope')}")
print(f"   expira en: {token_info.get('expires_in')} s")

sp = get_spotify_client(scopes=SCOPES_TOP_READ, cache_path=CACHE_CLI)
me = sp.me()
print(f"✅ Autenticado como: {me['display_name']} ({me['id']})")
