from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.run_backtest import run_backtest
from src.models.cards import score_card_models
from src.models.goals import score_goal_models
from src.models.shots import score_shot_models


def test_run_backtest_returns_match_level_predictions_and_leaderboard() -> None:
    feature_table = pd.DataFrame(
        [
            {
                "match_id": "m3",
                "match_date": "2026-06-13",
                "team": "Brazil",
                "target_name": "goals_for",
                "actual_value": 1.0,
                "hybrid_goals_signal": 1.8,
                "team_goals_avg_last_3": 1.8,
            },
            {
                "match_id": "m1",
                "match_date": "2026-06-11",
                "team": "Brazil",
                "target_name": "goals_for",
                "actual_value": 2.0,
                "hybrid_goals_signal": 1.4,
                "team_goals_avg_last_3": 1.4,
            },
            {
                "match_id": "m2",
                "match_date": "2026-06-12",
                "team": "Brazil",
                "target_name": "shots_for",
                "actual_value": 8.0,
                "hybrid_shots_signal": 9.0,
                "team_shots_avg_last_3": 9.0,
            },
        ]
    )

    outputs = run_backtest(feature_table)

    assert set(outputs.keys()) == {"predictions", "leaderboard"}
    assert outputs["predictions"][
        ["match_id", "team", "model_name", "target_name"]
    ].to_dict("records") == [
            {
                "match_id": "m1",
                "team": "Brazil",
                "model_name": "hybrid-prior",
                "target_name": "goals_for",
            },
            {
                "match_id": "m2",
                "team": "Brazil",
                "model_name": "hybrid-prior",
                "target_name": "shots_for",
            },
            {
                "match_id": "m3",
                "team": "Brazil",
                "model_name": "hybrid-prior",
                "target_name": "goals_for",
            },
        ]
    assert "mae" in outputs["leaderboard"].columns
    assert "observations" in outputs["leaderboard"].columns


def test_target_scoring_wrappers_use_family_fallbacks() -> None:
    goal_predictions = score_goal_models(
        pd.DataFrame(
            [
                {
                    "match_id": "g1",
                    "match_date": "2026-06-11",
                    "team": "Brazil",
                    "target_name": "goals_for",
                    "actual_value": 2.0,
                    "hybrid_goals_signal": 1.4,
                    "team_goals_avg_last_3": 1.4,
                }
            ]
        )
    )
    shot_predictions = score_shot_models(
        pd.DataFrame(
            [
                {
                    "match_id": "s1",
                    "match_date": "2026-06-11",
                    "team": "Brazil",
                    "target_name": "shots_for",
                    "actual_value": 7.0,
                    "hybrid_shots_signal": 8.5,
                    "team_shots_avg_last_3": 8.5,
                }
            ]
        )
    )

    assert goal_predictions.loc[0, "predicted_value"] == 1.4
    assert shot_predictions.loc[0, "predicted_value"] == 8.5


def test_score_card_models_returns_empty_when_cards_truth_is_unavailable() -> None:
    predictions = score_card_models(
        pd.DataFrame(
            [
                {
                    "match_id": "c1",
                    "match_date": "2026-06-11",
                    "team": "Brazil",
                    "target_name": "cards_for",
                    "actual_value": 2.0,
                    "team_cards_avg_last_3": 1.5,
                    "has_cards_truth": False,
                }
            ]
        )
    )

    assert predictions.empty
    assert list(predictions.columns) == [
        "match_id",
        "match_date",
        "team",
        "model_name",
        "target_name",
        "predicted_value",
        "actual_value",
    ]
