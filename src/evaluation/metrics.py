"""Metrics utilities for forecast backtests."""

import numpy as np
import pandas as pd

SUMMARY_COLUMNS = [
    "model_name",
    "target_name",
    "observations",
    "exact_hit_rate",
    "mae",
    "rmse",
    "bias",
]


def score_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate prediction quality metrics by model and target."""
    if predictions.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

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
            observations=("actual_value", "size"),
            exact_hit_rate=("exact_hit", "mean"),
            mae=("absolute_error", "mean"),
            mse=("squared_error", "mean"),
            bias=("prediction_error", "mean"),
        )
    )
    summary["rmse"] = np.sqrt(summary.pop("mse"))

    return summary[SUMMARY_COLUMNS]
