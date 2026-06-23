import pandas as pd

from src.models.baselines import empty_prediction_frame, get_baseline_spec, score_baseline_family

TARGET_NAME = "fouls_for"


def score_foul_models(feature_table: pd.DataFrame) -> pd.DataFrame:
    if feature_table.empty:
        return empty_prediction_frame()

    target_rows = feature_table.loc[feature_table["target_name"] == TARGET_NAME].copy()
    if target_rows.empty:
        return empty_prediction_frame()

    if "has_fouls_truth" in target_rows.columns:
        target_rows = target_rows.loc[target_rows["has_fouls_truth"].fillna(False)]
        if target_rows.empty:
            return empty_prediction_frame()

    spec = get_baseline_spec(TARGET_NAME)
    return score_baseline_family(
        target_rows,
        target_name=spec.target_name,
        feature_column=spec.feature_column,
        model_name=spec.model_name,
    )
