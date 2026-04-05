# recommender/profile.py
import pandas as pd

def get_user_profile_df(
    sp,
    time_range="medium_term",
    limit=50
) -> pd.DataFrame:
    res = sp.current_user_top_tracks(
        time_range=time_range,
        limit=min(limit, 50)
    )

    rows = []
    for t in res.get("items", []):
        rows.append({
            "track_id": t["id"],
            "track_name": t["name"],
            "artist_id": t["artists"][0]["id"],
            "artist_name": t["artists"][0]["name"],
            "popularity": t["popularity"],
            "genres": None  # si luego quieres enriquecer
        })

    return pd.DataFrame(rows)
