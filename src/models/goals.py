import pandas as pd

from src.models.baselines import get_baseline_spec, score_baseline_family

TARGET_NAME = "goals_for"


def score_goal_models(feature_table: pd.DataFrame) -> pd.DataFrame:
    spec = get_baseline_spec(TARGET_NAME)
    return score_baseline_family(
        feature_table,
        target_name=spec.target_name,
        feature_column=spec.feature_column,
        model_name=spec.model_name,
    )
