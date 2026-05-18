import pandas as pd
import numpy as np

LEAGUE_WEIGHTS = {
    "Premier League": 1.00,
    "La Liga": 0.95,
    "LaLiga": 0.95,
    "Serie A": 0.92,
    "Bundesliga": 0.90,
    "Ligue 1": 0.86,
    "Brasileirão Série A": 0.82,
    "Serie A Brazil": 0.82,
    "Pro League": 0.72,
    "Saudi Pro League": 0.72,
    "Premier League Russia": 0.70,
    "Süper Lig": 0.70,
}

POSITION_GROUPS = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Attacker": "ATT",
    "G": "GK",
    "D": "DEF",
    "M": "MID",
    "F": "ATT",
}

def per90(value, minutes):
    if pd.isna(minutes) or minutes <= 0:
        return 0
    return value / minutes * 90

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["goals_p90"] = df.apply(lambda r: per90(r.get("goals", 0), r.get("minutes", 0)), axis=1)
    df["assists_p90"] = df.apply(lambda r: per90(r.get("assists", 0), r.get("minutes", 0)), axis=1)
    df["goal_contributions"] = df["goals"].fillna(0) + df["assists"].fillna(0)
    df["goal_contributions_p90"] = df.apply(lambda r: per90(r.get("goal_contributions", 0), r.get("minutes", 0)), axis=1)

    df["key_passes_p90"] = df.apply(lambda r: per90(r.get("passes_key", 0), r.get("minutes", 0)), axis=1)
    df["tackles_p90"] = df.apply(lambda r: per90(r.get("tackles_total", 0), r.get("minutes", 0)), axis=1)
    df["interceptions_p90"] = df.apply(lambda r: per90(r.get("interceptions", 0), r.get("minutes", 0)), axis=1)

    df["duel_win_rate"] = np.where(
        df["duels_total"].fillna(0) > 0,
        df["duels_won"].fillna(0) / df["duels_total"].fillna(0),
        0
    )

    df["discipline_penalty"] = df["yellow_cards"].fillna(0) * 0.5 + df["red_cards"].fillna(0) * 2.0
    df["league_weight"] = df["league"].map(LEAGUE_WEIGHTS).fillna(0.75)
    df["position_group"] = df["position"].map(POSITION_GROUPS).fillna(df["position"])

    return df
