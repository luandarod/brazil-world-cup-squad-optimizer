from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.team_match_features import build_team_match_features


def test_build_team_match_features_adds_shifted_recent_form_averages() -> None:
    matches = pd.DataFrame(
        [
            {
                "match_id": "bra-3",
                "match_date": "2026-06-10",
                "team": "Brazil",
                "goals_for": 2,
                "cards_for": 1,
                "shots_for": 6,
            },
            {
                "match_id": "arg-2",
                "match_date": "2026-06-08",
                "team": "Argentina",
                "goals_for": 2,
                "cards_for": 2,
                "shots_for": 8,
            },
            {
                "match_id": "bra-1",
                "match_date": "2026-06-01",
                "team": "Brazil",
                "goals_for": 1,
                "cards_for": 2,
                "shots_for": 3,
            },
            {
                "match_id": "bra-4",
                "match_date": "2026-06-20",
                "team": "Brazil",
                "goals_for": 4,
                "cards_for": 3,
                "shots_for": 12,
            },
            {
                "match_id": "arg-1",
                "match_date": "2026-06-03",
                "team": "Argentina",
                "goals_for": 1,
                "cards_for": 4,
                "shots_for": 5,
            },
            {
                "match_id": "bra-2",
                "match_date": "2026-06-05",
                "team": "Brazil",
                "goals_for": 3,
                "cards_for": 4,
                "shots_for": 9,
            },
        ]
    )
    original_matches = matches.copy(deep=True)

    featured = build_team_match_features(matches)

    assert matches.equals(original_matches)
    assert featured["match_id"].tolist() == matches["match_id"].tolist()
    assert str(featured["match_date"].dtype) == "datetime64[ns]"
    feature_columns = [
        "team_goals_avg_last_3",
        "team_cards_avg_last_3",
        "team_shots_avg_last_3",
    ]
    feature_by_match = (
        featured.set_index("match_id")[feature_columns].round(6).to_dict("index")
    )

    assert feature_by_match == {
        "bra-3": {
            "team_goals_avg_last_3": 2.0,
            "team_cards_avg_last_3": 3.0,
            "team_shots_avg_last_3": 6.0,
        },
        "arg-2": {
            "team_goals_avg_last_3": 1.0,
            "team_cards_avg_last_3": 4.0,
            "team_shots_avg_last_3": 5.0,
        },
        "bra-1": {
            "team_goals_avg_last_3": 0.0,
            "team_cards_avg_last_3": 0.0,
            "team_shots_avg_last_3": 0.0,
        },
        "bra-4": {
            "team_goals_avg_last_3": 2.0,
            "team_cards_avg_last_3": 2.333333,
            "team_shots_avg_last_3": 6.0,
        },
        "arg-1": {
            "team_goals_avg_last_3": 0.0,
            "team_cards_avg_last_3": 0.0,
            "team_shots_avg_last_3": 0.0,
        },
        "bra-2": {
            "team_goals_avg_last_3": 1.0,
            "team_cards_avg_last_3": 2.0,
            "team_shots_avg_last_3": 3.0,
        },
    }
