from recommender.auth import get_spotify_client
from recommender.recommendations import generate_recommendations

import pandas as pd
import random

# =========================
# Configuración
# =========================
FINAL_SIZE = 15
CACHE_PATH = ".cache-recommendations"

SPOTIFY_SCOPES = [
    "user-top-read",
]

# =========================
# Main
# =========================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Python Spotify Recommender — Discovery mode"
    )
    parser.add_argument("--features-csv", required=True)
    parser.add_argument("--out", default="recommendations_final.csv")
    parser.add_argument("--discovery", action="store_true", default=True)
    parser.add_argument("--seed", type=int, help="Semilla aleatoria (opcional)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    print("▶︎ Cargando CSV de Top Tracks …")
    df = pd.read_csv(args.features_csv)

    print("▶︎ Autenticando con Spotify …")
    sp = get_spotify_client(
        scopes=SPOTIFY_SCOPES,
        cache_path=CACHE_PATH
    )

    print("▶︎ Generando recomendaciones …")
    final_tracks = generate_recommendations(
        sp=sp,
        top_df=df,
        discovery=args.discovery,
        size=FINAL_SIZE
    )

    if not final_tracks:
        print("⚠️ No se generaron recomendaciones.")
        return

    print(f"\n🎧 Recomendaciones finales ({len(final_tracks)}):\n")
    for i, t in enumerate(final_tracks, 1):
        print(f"{i:02d}. {t['track_name']} — {t['artist_name']}")

    df_out = pd.DataFrame(final_tracks)
    df_out.to_csv(args.out, index=False, encoding="utf-8")

    print(f"\n✅ CSV generado → {args.out}")

if __name__ == "__main__":
    main()
