from dataclasses import dataclass

import pandas as pd

PREDICTION_COLUMNS = [
    "match_id",
    "match_date",
    "team",
    "model_name",
    "target_name",
    "predicted_value",
    "actual_value",
]
LEGACY_FEATURE_COLUMNS = {
    "goals_for": "team_goals_avg_last_3",
    "shots_for": "team_shots_avg_last_3",
    "cards_for": "team_cards_avg_last_3",
    "fouls_for": "team_fouls_avg_last_3",
}


@dataclass(frozen=True)
class BaselineModelSpec:
    model_name: str
    target_name: str
    feature_column: str


def default_baseline_specs() -> list[BaselineModelSpec]:
    return [
        BaselineModelSpec(
            model_name="hybrid-prior",
            target_name="goals_for",
            feature_column="hybrid_goals_signal",
        ),
        BaselineModelSpec(
            model_name="hybrid-prior",
            target_name="shots_for",
            feature_column="hybrid_shots_signal",
        ),
        BaselineModelSpec(
            model_name="hybrid-prior",
            target_name="cards_for",
            feature_column="hybrid_cards_signal",
        ),
        BaselineModelSpec(
            model_name="hybrid-prior",
            target_name="fouls_for",
            feature_column="hybrid_fouls_signal",
        ),
    ]


def get_baseline_spec(target_name: str) -> BaselineModelSpec:
    for spec in default_baseline_specs():
        if spec.target_name == target_name:
            return spec
    raise KeyError(f"Unsupported target for baselines: {target_name}")


def empty_prediction_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=PREDICTION_COLUMNS)


def score_baseline_family(
    feature_table: pd.DataFrame,
    *,
    target_name: str,
    feature_column: str,
    model_name: str = "hybrid-prior",
) -> pd.DataFrame:
    if feature_table.empty:
        return empty_prediction_frame()
    resolved_feature_column = feature_column
    if resolved_feature_column not in feature_table.columns:
        resolved_feature_column = LEGACY_FEATURE_COLUMNS.get(target_name, feature_column)
    if resolved_feature_column not in feature_table.columns:
        return empty_prediction_frame()

    target_rows = feature_table.loc[
        feature_table["target_name"] == target_name
    ].copy()
    if target_rows.empty:
        return empty_prediction_frame()

    if "actual_value" not in target_rows.columns:
        return empty_prediction_frame()

    target_rows["model_name"] = model_name
    target_rows["predicted_value"] = target_rows[resolved_feature_column].astype(float)
    target_rows["actual_value"] = target_rows["actual_value"].astype(float)

    if "match_date" in target_rows.columns:
        target_rows = target_rows.sort_values(
            ["match_date", "match_id", "team"], kind="stable"
        )

    for column in PREDICTION_COLUMNS:
        if column not in target_rows.columns:
            target_rows[column] = None

    return target_rows[PREDICTION_COLUMNS].reset_index(drop=True)
