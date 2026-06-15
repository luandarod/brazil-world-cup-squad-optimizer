"""Metrics utilities for forecast backtests."""

import numpy as np
import pandas as pd


def score_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate prediction quality metrics by model and target."""
    scored = predictions.copy()
    scored["prediction_error"] = (
        scored["predicted_value"].astype(float) - scored["actual_value"].astype(float)
    )
    scored["absolute_error"] = scored["prediction_error"].abs()
    scored["squared_error"] = scored["prediction_error"] ** 2
    scored["exact_hit"] = (
        scored["predicted_value"].round() == scored["actual_value"]
    ).astype(float)

    summary = (
        scored.groupby(["model_name", "target_name"], as_index=False)
        .agg(
            exact_hit_rate=("exact_hit", "mean"),
            mae=("absolute_error", "mean"),
            mse=("squared_error", "mean"),
            bias=("prediction_error", "mean"),
        )
    )
    summary["rmse"] = np.sqrt(summary.pop("mse"))

    return summary[["model_name", "target_name", "exact_hit_rate", "mae", "rmse", "bias"]]
