from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.metrics import score_predictions


def test_score_predictions_returns_grouped_metrics_summary() -> None:
    predictions = pd.DataFrame(
        [
            {
                "model_name": "baseline",
                "target_name": "goals",
                "predicted_value": 1.2,
                "actual_value": 1.0,
            },
            {
                "model_name": "baseline",
                "target_name": "goals",
                "predicted_value": 2.7,
                "actual_value": 2.0,
            },
            {
                "model_name": "baseline",
                "target_name": "shots",
                "predicted_value": 8.2,
                "actual_value": 8.0,
            },
            {
                "model_name": "xgboost",
                "target_name": "goals",
                "predicted_value": 1.6,
                "actual_value": 2.0,
            },
            {
                "model_name": "xgboost",
                "target_name": "goals",
                "predicted_value": 0.4,
                "actual_value": 1.0,
            },
        ]
    )

    scored = score_predictions(predictions).sort_values(
        ["model_name", "target_name"]
    ).reset_index(drop=True)

    expected = pd.DataFrame(
        [
            {
                "model_name": "baseline",
                "target_name": "goals",
                "observations": 2,
                "exact_hit_rate": 0.5,
                "mae": 0.45,
                "rmse": (0.265) ** 0.5,
                "bias": 0.45,
            },
            {
                "model_name": "baseline",
                "target_name": "shots",
                "observations": 1,
                "exact_hit_rate": 1.0,
                "mae": 0.2,
                "rmse": 0.2,
                "bias": 0.2,
            },
            {
                "model_name": "xgboost",
                "target_name": "goals",
                "observations": 2,
                "exact_hit_rate": 0.5,
                "mae": 0.5,
                "rmse": (0.26) ** 0.5,
                "bias": -0.5,
            },
        ]
    )

    pd.testing.assert_frame_equal(scored, expected, check_exact=False, atol=1e-6)


def test_score_predictions_keeps_target_level_metrics_separate() -> None:
    predictions = pd.DataFrame(
        [
            {
                "model_name": "moving-average",
                "target_name": "goals_for",
                "predicted_value": 1.5,
                "actual_value": 2.0,
            },
            {
                "model_name": "moving-average",
                "target_name": "shots_for",
                "predicted_value": 9.0,
                "actual_value": 8.0,
            },
        ]
    )

    scored = score_predictions(predictions)

    assert scored["target_name"].tolist() == ["goals_for", "shots_for"]
    assert scored["observations"].tolist() == [1, 1]
