import pandas as pd
import numpy as np

NUMERIC_COLUMNS = [
    "appearances", "lineups", "minutes", "rating", "goals", "assists",
    "shots_total", "shots_on", "passes_total", "passes_key", "passes_accuracy",
    "yellow_cards", "red_cards", "duels_total", "duels_won", "tackles_total",
    "interceptions"
]

def clean_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    fill_zero_cols = [col for col in NUMERIC_COLUMNS if col != "rating" and col in df.columns]
    df[fill_zero_cols] = df[fill_zero_cols].fillna(0)

    if "minutes" in df.columns:
        df = df[df["minutes"].fillna(0) > 0]

    df["player_name"] = df["player_name"].astype(str).str.strip()
    df["team"] = df["team"].astype(str).str.strip()
    df["league"] = df["league"].astype(str).str.strip()

    return df.reset_index(drop=True)

def aggregate_player_season(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega estatísticas de um jogador quando ele aparece em mais de uma competição.
    """
    numeric_cols = [c for c in NUMERIC_COLUMNS if c in df.columns]
    group_cols = ["player_id", "player_name", "age", "nationality", "position"]

    agg_dict = {col: "sum" for col in numeric_cols if col != "rating"}
    if "rating" in df.columns:
        agg_dict["rating"] = "mean"

    result = df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()

    teams = df.groupby("player_id")["team"].agg(lambda x: ", ".join(sorted(set(x.dropna())))).reset_index()
    leagues = df.groupby("player_id")["league"].agg(lambda x: ", ".join(sorted(set(x.dropna())))).reset_index()

    result = result.merge(teams, on="player_id", how="left")
    result = result.merge(leagues, on="player_id", how="left")

    return result
