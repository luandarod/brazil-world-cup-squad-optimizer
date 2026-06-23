"""Backtest execution entrypoint."""

import pandas as pd

from src.models.baselines import empty_prediction_frame
from src.evaluation.metrics import score_predictions
from src.models.cards import score_card_models
from src.models.fouls import score_foul_models
from src.models.goals import score_goal_models
from src.models.shots import score_shot_models


def run_backtest(feature_table: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if feature_table.empty:
        empty_leaderboard = score_predictions(empty_prediction_frame())
        return {
            "predictions": empty_prediction_frame(),
            "leaderboard": empty_leaderboard,
        }

    ordered = feature_table.sort_values(
        ["match_date", "match_id", "team"], kind="stable"
    ).reset_index(drop=True)
    prediction_frames = [
        frame
        for frame in [
            score_goal_models(ordered),
            score_shot_models(ordered),
            score_card_models(ordered),
            score_foul_models(ordered),
        ]
        if not frame.empty
    ]
    predictions = (
        pd.concat(prediction_frames, ignore_index=True)
        if prediction_frames
        else empty_prediction_frame()
    )

    if not predictions.empty:
        predictions = predictions.sort_values(
            ["match_date", "match_id", "team", "target_name"], kind="stable"
        ).reset_index(drop=True)

    leaderboard = score_predictions(predictions)
    return {"predictions": predictions, "leaderboard": leaderboard}
