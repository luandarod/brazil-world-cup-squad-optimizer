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

DEFAULT_WEIGHTS = {
    "minutes": 0.20,
    "rating": 0.20,
    "league_weight": 0.15,
    "goal_contributions_p90": 0.15,
    "key_passes_p90": 0.10,
    "tackles_p90": 0.10,
    "interceptions_p90": 0.05,
    "duel_win_rate": 0.05,
}

def calculate_scores(df: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    df = normalize_features(df, SCORE_FEATURES)
    df = df.copy()

    for col in [f"{f}_norm" for f in SCORE_FEATURES]:
        if col not in df.columns:
            df[col] = 0

    # Resolve and normalize weights
    w = DEFAULT_WEIGHTS.copy()
    if weights is not None:
        for k, v in weights.items():
            if k in w:
                w[k] = float(v)
    
    total_w = sum(w.values())
    if total_w > 0:
        w_norm = {k: v / total_w for k, v in w.items()}
    else:
        w_norm = {k: 0.0 for k in w}

    df["base_score"] = (
        w_norm.get("minutes", 0.20) * df["minutes_norm"] +
        w_norm.get("rating", 0.20) * df["rating_norm"] +
        w_norm.get("league_weight", 0.15) * df["league_weight_norm"] +
        w_norm.get("goal_contributions_p90", 0.15) * df["goal_contributions_p90_norm"] +
        w_norm.get("key_passes_p90", 0.10) * df["key_passes_p90_norm"] +
        w_norm.get("tackles_p90", 0.10) * df["tackles_p90_norm"] +
        w_norm.get("interceptions_p90", 0.05) * df["interceptions_p90_norm"] +
        w_norm.get("duel_win_rate", 0.05) * df["duel_win_rate_norm"]
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
