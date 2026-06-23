from __future__ import annotations

import pandas as pd

from src.features.player_context_features import build_player_context_features


def _series_or_default(featured: pd.DataFrame, column: str) -> pd.Series:
    if column in featured.columns:
        return pd.to_numeric(featured[column], errors="coerce").fillna(0.0)
    return pd.Series([0.0] * len(featured), index=featured.index, dtype=float)


def build_team_match_features(matches: pd.DataFrame) -> pd.DataFrame:
    featured = build_player_context_features(matches)
    featured["_original_row_order"] = range(len(featured))
    featured["match_date"] = pd.to_datetime(featured["match_date"])
    featured = featured.sort_values(["team", "match_date", "_original_row_order"]).reset_index(
        drop=True
    )

    feature_specs = {
        "goals_for": "team_goals_avg_last_3",
        "cards_for": "team_cards_avg_last_3",
        "shots_for": "team_shots_avg_last_3",
        "fouls_for": "team_fouls_avg_last_3",
    }

    for source_column, feature_column in feature_specs.items():
        if source_column not in featured.columns:
            featured[source_column] = 0.0
        featured[feature_column] = (
            featured.groupby("team")[source_column]
            .transform(lambda values: values.shift(1).rolling(3, min_periods=1).mean())
            .fillna(0.0)
        )

    featured["matches_before"] = featured.groupby("team").cumcount().astype(float)
    history_weight = (featured["matches_before"] / 3.0).clip(lower=0.0, upper=1.0)
    lineup_attack_adjustment = (
        0.94
        + featured["probable_lineup_completeness"].fillna(0.0) * 0.05
        + featured["lineup_confirmed_flag"].fillna(0.0) * 0.01
    ).clip(lower=0.9, upper=1.02)

    hybrid_specs = {
        "hybrid_goals_signal": ("team_goals_prior", "team_goals_avg_last_3", lineup_attack_adjustment),
        "hybrid_shots_signal": ("team_shots_prior", "team_shots_avg_last_3", lineup_attack_adjustment),
        "hybrid_cards_signal": ("team_cards_prior", "team_cards_avg_last_3", 1.0),
        "hybrid_fouls_signal": ("team_fouls_prior", "team_fouls_avg_last_3", 1.0),
    }
    for target_column, (prior_column, recent_column, multiplier) in hybrid_specs.items():
        prior_values = _series_or_default(featured, prior_column)
        recent_values = _series_or_default(featured, recent_column)
        signal = prior_values * (1.0 - history_weight) + recent_values * history_weight
        featured[target_column] = (signal * multiplier).astype(float)

    return (
        featured.sort_values("_original_row_order")
        .drop(columns=["_original_row_order", "matches_before"])
        .reset_index(drop=True)
    )
