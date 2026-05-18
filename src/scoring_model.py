import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

SCORE_FEATURES = [
    "minutes",
    "rating",
    "league_weight",
    "goals_p90",
    "assists_p90",
    "goal_contributions_p90",
    "key_passes_p90",
    "tackles_p90",
    "interceptions_p90",
    "duel_win_rate",
]

def normalize_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    df = df.copy()
    valid_features = [f for f in features if f in df.columns]
    df[valid_features] = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0)

    scaler = MinMaxScaler()
    df[[f"{f}_norm" for f in valid_features]] = scaler.fit_transform(df[valid_features])

    return df

def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_features(df, SCORE_FEATURES)
    df = df.copy()

    for col in [f"{f}_norm" for f in SCORE_FEATURES]:
        if col not in df.columns:
            df[col] = 0

    df["base_score"] = (
        0.20 * df["minutes_norm"] +
        0.20 * df["rating_norm"] +
        0.15 * df["league_weight_norm"] +
        0.15 * df["goal_contributions_p90_norm"] +
        0.10 * df["key_passes_p90_norm"] +
        0.10 * df["tackles_p90_norm"] +
        0.05 * df["interceptions_p90_norm"] +
        0.05 * df["duel_win_rate_norm"]
    )

    df["minutes_bonus"] = np.where(df["minutes"] >= 1800, 0.05, 0)
    df["low_minutes_penalty"] = np.where(df["minutes"] < 600, 0.10, 0)
    df["discipline_penalty_norm"] = np.minimum(df.get("discipline_penalty", 0) / 10, 0.10)

    df["score_final"] = (
        df["base_score"] +
        df["minutes_bonus"] -
        df["low_minutes_penalty"] -
        df["discipline_penalty_norm"]
    )

    df["score_final"] = (df["score_final"].clip(0, 1) * 100).round(1)

    return df.sort_values("score_final", ascending=False).reset_index(drop=True)
