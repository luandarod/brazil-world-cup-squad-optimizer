from __future__ import annotations

import pandas as pd


def build_team_match_features(matches: pd.DataFrame) -> pd.DataFrame:
    featured = matches.copy()
    featured["match_date"] = pd.to_datetime(featured["match_date"])
    featured = featured.sort_values(["team", "match_date"]).reset_index(drop=True)

    feature_specs = {
        "goals_for": "team_goals_avg_last_3",
        "cards_for": "team_cards_avg_last_3",
        "shots_for": "team_shots_avg_last_3",
    }

    for source_column, feature_column in feature_specs.items():
        featured[feature_column] = (
            featured.groupby("team")[source_column]
            .transform(lambda values: values.shift(1).rolling(3, min_periods=1).mean())
            .fillna(0.0)
        )

    return featured
