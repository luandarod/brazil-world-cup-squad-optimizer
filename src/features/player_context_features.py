from __future__ import annotations

import pandas as pd


def _series_from_candidates(
    matches: pd.DataFrame,
    candidates: list[str],
    default: float | bool = 0.0,
) -> pd.Series:
    for column in candidates:
        if column in matches.columns:
            return matches[column]
    return pd.Series([default] * len(matches), index=matches.index)


def build_player_context_features(
    matches: pd.DataFrame,
    team_column: str = "team",
) -> pd.DataFrame:
    featured = matches.copy()

    if team_column not in featured.columns:
        raise KeyError(f"Missing required team column: {team_column}")

    lineup_confirmed = _series_from_candidates(
        featured,
        ["lineup_confirmed_flag", "home_lineup_confirmed", "away_lineup_confirmed"],
        default=False,
    )
    probable_lineup_count = _series_from_candidates(
        featured,
        [
            "probable_lineup_count",
            "home_probable_lineup_count",
            "away_probable_lineup_count",
        ],
        default=0.0,
    )
    substitutions_used = _series_from_candidates(
        featured,
        ["substitutions_used", "home_substitutions_used", "away_substitutions_used"],
        default=0.0,
    )
    player_minutes_proxy = _series_from_candidates(
        featured,
        ["player_minutes_proxy", "home_player_minutes_proxy", "away_player_minutes_proxy"],
        default=0.0,
    )

    featured["lineup_confirmed_flag"] = lineup_confirmed.fillna(False).astype(float)
    featured["probable_lineup_completeness"] = (
        probable_lineup_count.fillna(0.0).astype(float) / 11.0
    ).clip(lower=0.0, upper=1.0)
    featured["bench_usage_rate"] = (
        substitutions_used.fillna(0.0).astype(float) / 5.0
    ).clip(lower=0.0, upper=1.0)
    featured["player_minutes_load_ratio"] = (
        player_minutes_proxy.fillna(0.0).astype(float) / 990.0
    ).clip(lower=0.0, upper=1.0)

    return featured
