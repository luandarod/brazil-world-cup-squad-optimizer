from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Iterable

import pandas as pd
import numpy as np

from src.pipelines.ingest_sources import (
    _normalize_team_name,
    _parse_date,
    PUBLIC_MATCH_COLUMNS,
    TOURNAMENT_FINAL_DATE,
)
from src.pipelines.process_features import (
    _read_team_metrics,
    TOP_SCORER_COLUMNS,
)

LEADERBOARD_COLUMNS = [
    "model_name",
    "target_name",
    "observations",
    "exact_hit_rate",
    "mae",
    "rmse",
    "bias",
]

PREDICTION_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "model_name",
    "status",
    "is_future_fixture",
    "predicted_home_goals",
    "predicted_away_goals",
    "predicted_home_shots",
    "predicted_away_shots",
    "predicted_home_cards",
    "predicted_away_cards",
    "predicted_home_fouls",
    "predicted_away_fouls",
    "predicted_winner",
]

MATCH_COMPARISON_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "model_name",
    "predicted_home_goals",
    "predicted_away_goals",
    "predicted_home_shots",
    "predicted_away_shots",
    "predicted_home_cards",
    "predicted_away_cards",
    "predicted_home_fouls",
    "predicted_away_fouls",
    "predicted_winner",
    "actual_home_goals",
    "actual_away_goals",
    "actual_home_shots",
    "actual_away_shots",
    "actual_home_cards",
    "actual_away_cards",
    "actual_home_fouls",
    "actual_away_fouls",
    "actual_winner",
    "goal_error_home",
    "goal_error_away",
    "shot_error_home",
    "shot_error_away",
    "card_error_home",
    "card_error_away",
    "foul_error_home",
    "foul_error_away",
    "winner_hit",
]

GROUP_FORECAST_COLUMNS = [
    "group_stage",
    "team",
    "matches_played",
    "matches_remaining",
    "observed_points",
    "projected_points",
    "projected_total_points",
    "observed_goal_difference",
    "projected_goal_difference",
    "projected_total_goal_difference",
]

KNOCKOUT_FORECAST_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "model_name",
    "predicted_home_goals",
    "predicted_away_goals",
    "predicted_home_shots",
    "predicted_away_shots",
    "predicted_home_cards",
    "predicted_away_cards",
    "predicted_home_fouls",
    "predicted_away_fouls",
    "predicted_winner",
]

TEAM_FORECAST_COLUMNS = [
    "team",
    "matches_played",
    "observed_points",
    "projected_points",
    "forecast_total_points",
    "observed_goals_for",
    "projected_goals_for",
    "forecast_total_goals_for",
    "observed_cards_for",
    "projected_cards_for",
    "forecast_total_cards_for",
    "observed_fouls_for",
    "projected_fouls_for",
    "forecast_total_fouls_for",
]

METHODOLOGY_STATUS_COLUMNS = [
    "metric_name",
    "has_truth",
    "truth_coverage_pct",
    "has_predictions",
    "publish_status",
]

TITLE_PROBABILITY_COLUMNS = [
    "team",
    "strength_rating",
    "projected_total_points",
    "projected_total_goals_for",
    "projected_stage",
    "title_probability",
    "title_probability_pct",
    "final_probability_pct",
    "semifinal_probability_pct",
]

TEAM_SUMMARY_COLUMNS = [
    "team",
    "matches_played",
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "shots_for",
    "cards_for",
    "fouls_for",
    "goal_difference",
    "points",
]

def _merge_prediction_context(
    predictions: pd.DataFrame,
    feature_table: pd.DataFrame,
) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame()

    context_columns = [
        "match_id",
        "match_date",
        "stage",
        "status",
        "home_team",
        "away_team",
        "team",
        "is_home",
        "is_future_fixture",
        "target_name",
    ]
    merged = predictions.merge(
        feature_table[context_columns],
        on=["match_id", "match_date", "team", "target_name"],
        how="left",
    )
    return merged



def _build_future_side_predictions(
    future_featured_history: pd.DataFrame,
    coverage: pd.DataFrame,
) -> pd.DataFrame:
    if future_featured_history.empty:
        return pd.DataFrame()

    target_specs = [
        ("goals_for", "hybrid_goals_signal"),
        ("shots_for", "hybrid_shots_signal"),
    ]
    target_specs.append(("cards_for", "hybrid_cards_signal"))
    if bool(coverage.loc[coverage["metric_name"] == "fouls", "has_truth"].fillna(False).any()):
        target_specs.append(("fouls_for", "hybrid_fouls_signal"))

    rows: list[dict] = []
    for match in future_featured_history.to_dict("records"):
        for target_name, feature_column in target_specs:
            rows.append(
                {
                    "match_id": str(match["match_id"]),
                    "match_date": match["match_date"],
                    "stage": match["stage"],
                    "status": match["status"],
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "team": match["team"],
                    "is_home": bool(match["is_home"]),
                    "is_future_fixture": True,
                    "model_name": "hybrid-prior",
                    "target_name": target_name,
                    "predicted_value": float(match.get(feature_column, 0.0)),
                    "actual_value": float("nan"),
                }
            )
    return pd.DataFrame(rows)



def _combine_side_predictions(
    observed_side_predictions: pd.DataFrame,
    future_side_predictions: pd.DataFrame,
) -> pd.DataFrame:
    frames = [frame for frame in [observed_side_predictions, future_side_predictions] if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(
        ["match_date", "match_id", "team", "target_name"],
        kind="stable",
    ).reset_index(drop=True)



def _build_public_match_predictions(side_predictions: pd.DataFrame) -> pd.DataFrame:
    if side_predictions.empty:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)

    records: list[dict] = []
    group_columns = [
        "match_id",
        "match_date",
        "stage",
        "home_team",
        "away_team",
        "model_name",
        "status",
        "is_future_fixture",
    ]
    grouped = side_predictions.groupby(group_columns, dropna=False, sort=False)
    for keys, frame in grouped:
        row = dict(zip(group_columns, keys))
        row["predicted_home_goals"] = _lookup_predicted_metric(frame, True, "goals_for")
        row["predicted_away_goals"] = _lookup_predicted_metric(frame, False, "goals_for")
        row["predicted_home_shots"] = _lookup_predicted_metric(frame, True, "shots_for")
        row["predicted_away_shots"] = _lookup_predicted_metric(frame, False, "shots_for")
        row["predicted_home_cards"] = _lookup_predicted_metric(frame, True, "cards_for")
        row["predicted_away_cards"] = _lookup_predicted_metric(frame, False, "cards_for")
        row["predicted_home_fouls"] = _lookup_predicted_metric(frame, True, "fouls_for")
        row["predicted_away_fouls"] = _lookup_predicted_metric(frame, False, "fouls_for")
        row["predicted_winner"] = _derive_winner(
            row["predicted_home_goals"],
            row["predicted_away_goals"],
            row["home_team"],
            row["away_team"],
        )
        records.append(row)

    return pd.DataFrame(records, columns=PREDICTION_COLUMNS).sort_values(
        ["match_date", "match_id"],
        kind="stable",
    ).reset_index(drop=True)



def _combine_match_predictions(
    observed_predictions: pd.DataFrame,
    future_predictions: pd.DataFrame,
) -> pd.DataFrame:
    frames = [frame for frame in [observed_predictions, future_predictions] if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    return pd.concat(frames, ignore_index=True).sort_values(
        ["match_date", "match_id"],
        kind="stable",
    ).reset_index(drop=True)



def _build_future_match_predictions(
    *,
    future_fixtures: pd.DataFrame,
    observed_results: pd.DataFrame,
    team_priors: dict[str, dict[str, float]],
) -> pd.DataFrame:
    if future_fixtures.empty:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)

    team_context = _build_team_context(team_priors, observed_results)
    group_fixtures = future_fixtures.loc[
        future_fixtures["stage"].astype(str).str.startswith("Group ")
    ].copy()
    group_records = [
        _predict_match_record(
            fixture=row,
            home_team=str(row["home_team"]),
            away_team=str(row["away_team"]),
            team_context=team_context,
            knockout=False,
        )
        for row in group_fixtures.to_dict("records")
    ]
    group_predictions = pd.DataFrame(group_records, columns=PREDICTION_COLUMNS)

    standings_by_group = _build_group_rankings(
        observed_results=observed_results,
        group_predictions=group_predictions,
    )
    ranked_third_places = _build_ranked_third_places(standings_by_group)
    knockout_predictions = _build_knockout_predictions(
        future_fixtures=future_fixtures.loc[
            ~future_fixtures["stage"].astype(str).str.startswith("Group ")
        ].copy(),
        standings_by_group=standings_by_group,
        ranked_third_places=ranked_third_places,
        team_context=team_context,
    )
    return _combine_match_predictions(group_predictions, knockout_predictions)



def _build_team_context(
    team_priors: dict[str, dict[str, float]],
    observed_results: pd.DataFrame,
) -> dict[str, dict[str, float]]:
    lookup = {
        team: metrics.copy()
        for team, metrics in team_priors.items()
    }
    if observed_results.empty:
        return lookup

    observed_team_summary = _build_team_summary(observed_results)
    if observed_team_summary.empty:
        return lookup
    context = observed_team_summary.copy()
    context["matches_played"] = pd.to_numeric(context["matches_played"], errors="coerce").fillna(0.0)
    safe_matches = context["matches_played"].replace(0, 1)

    for row in context.to_dict("records"):
        team_name = str(row["team"])
        prior_metrics = _read_team_metrics(team_priors, team_name)
        form_weight = min(0.55, float(row["matches_played"]) / 6.0)
        observed_goals_for = float(row["goals_for"]) / float(max(row["matches_played"], 1))
        observed_goals_against = float(row["goals_against"]) / float(max(row["matches_played"], 1))
        observed_shots = float(row.get("shots_for", 0.0)) / float(max(row["matches_played"], 1))
        observed_cards = float(row.get("cards_for", 0.0)) / float(max(row["matches_played"], 1))
        observed_fouls = float(row.get("fouls_for", 0.0)) / float(max(row["matches_played"], 1))
        lookup[team_name] = {
            "goals_for_avg": round(prior_metrics["goals_for_avg"] * (1.0 - form_weight) + observed_goals_for * form_weight, 2),
            "goals_against_avg": round(prior_metrics["goals_against_avg"] * (1.0 - form_weight) + observed_goals_against * form_weight, 2),
            "shots_for_avg": round(prior_metrics["shots_for_avg"] * (1.0 - form_weight) + observed_shots * form_weight, 2),
            "cards_for_avg": round(prior_metrics["cards_for_avg"] * (1.0 - form_weight) + observed_cards * form_weight, 2),
            "fouls_for_avg": round(prior_metrics["fouls_for_avg"] * (1.0 - form_weight) + observed_fouls * form_weight, 2),
            "points_per_match": round(prior_metrics["points_per_match"] * (1.0 - form_weight) + float(row["points"]) / float(max(row["matches_played"], 1)) * form_weight, 2),
            "goal_diff_per_match": round(prior_metrics["goal_diff_per_match"] * (1.0 - form_weight) + float(row["goal_difference"]) / float(max(row["matches_played"], 1)) * form_weight, 2),
            "strength_rating": prior_metrics["strength_rating"],
        }
    return lookup



def _predict_match_record(
    *,
    fixture: dict,
    home_team: str,
    away_team: str,
    team_context: dict[str, dict[str, float]],
    knockout: bool,
) -> dict:
    home_metrics = _read_team_metrics(team_context, home_team)
    away_metrics = _read_team_metrics(team_context, away_team)

    home_goals = _project_goals(home_metrics, away_metrics, home_advantage=0.14 if not knockout else 0.05)
    away_goals = _project_goals(away_metrics, home_metrics, home_advantage=0.0)
    predicted_winner = _pick_predicted_winner(
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        home_metrics=home_metrics,
        away_metrics=away_metrics,
        knockout=knockout,
    )

    return {
        "match_id": str(fixture["match_id"]),
        "match_date": fixture["match_date"],
        "stage": fixture["stage"],
        "home_team": home_team,
        "away_team": away_team,
        "model_name": "hybrid-prior",
        "status": fixture["status"],
        "is_future_fixture": True,
        "predicted_home_goals": home_goals,
        "predicted_away_goals": away_goals,
        "predicted_home_shots": _project_shots(home_metrics, home_goals),
        "predicted_away_shots": _project_shots(away_metrics, away_goals),
        "predicted_home_cards": _project_cards(home_metrics, home_goals),
        "predicted_away_cards": _project_cards(away_metrics, away_goals),
        "predicted_home_fouls": _project_fouls(home_metrics, home_goals),
        "predicted_away_fouls": _project_fouls(away_metrics, away_goals),
        "predicted_winner": predicted_winner,
    }



def _project_goals(
    attack_metrics: dict[str, float],
    defense_metrics: dict[str, float],
    *,
    home_advantage: float,
) -> float:
    projected = (
        attack_metrics["goals_for_avg"] * 0.62
        + defense_metrics["goals_against_avg"] * 0.38
        + home_advantage
    )
    return round(min(max(projected, 0.2), 4.5), 1)



def _project_shots(team_metrics: dict[str, float], projected_goals: float) -> float:
    projected = team_metrics["shots_for_avg"] * 0.72 + projected_goals * 2.15
    return round(min(max(projected, 4.0), 28.0), 1)



def _project_cards(team_metrics: dict[str, float], projected_goals: float) -> float:
    projected = team_metrics["cards_for_avg"] * 0.9 + max(0.0, 1.8 - projected_goals) * 0.15
    return round(min(max(projected, 0.6), 5.5), 1)



def _project_fouls(team_metrics: dict[str, float], projected_goals: float) -> float:
    projected = team_metrics["fouls_for_avg"] * 0.92 + max(0.0, 1.8 - projected_goals) * 0.6
    return round(min(max(projected, 5.0), 22.0), 1)



def _pick_predicted_winner(
    *,
    home_team: str,
    away_team: str,
    home_goals: float,
    away_goals: float,
    home_metrics: dict[str, float],
    away_metrics: dict[str, float],
    knockout: bool,
) -> str:
    if home_goals > away_goals:
        return home_team
    if away_goals > home_goals:
        return away_team

    strength_gap = (
        home_metrics["points_per_match"] - away_metrics["points_per_match"]
        + home_metrics["goal_diff_per_match"] - away_metrics["goal_diff_per_match"]
    )
    if strength_gap >= 0:
        return home_team if knockout else "Draw"
    return away_team if knockout else "Draw"



def _build_group_rankings(
    *,
    observed_results: pd.DataFrame,
    group_predictions: pd.DataFrame,
) -> dict[str, list[dict]]:
    rows: list[dict] = []
    for match in observed_results.to_dict("records"):
        if not str(match["stage"]).startswith("Group "):
            continue
        rows.extend(
            [
                {
                    "group_stage": match["stage"],
                    "team": match["home_team"],
                    "points": _points_for_outcome(_coerce_float(match["home_goals"]), _coerce_float(match["away_goals"])),
                    "goal_difference": _coerce_float(match["home_goals"]) - _coerce_float(match["away_goals"]),
                    "goals_for": _coerce_float(match["home_goals"]),
                },
                {
                    "group_stage": match["stage"],
                    "team": match["away_team"],
                    "points": _points_for_outcome(_coerce_float(match["away_goals"]), _coerce_float(match["home_goals"])),
                    "goal_difference": _coerce_float(match["away_goals"]) - _coerce_float(match["home_goals"]),
                    "goals_for": _coerce_float(match["away_goals"]),
                },
            ]
        )
    for match in group_predictions.to_dict("records"):
        rows.extend(
            [
                {
                    "group_stage": match["stage"],
                    "team": match["home_team"],
                    "points": _points_for_outcome(
                        _coerce_float(match["predicted_home_goals"]),
                        _coerce_float(match["predicted_away_goals"]),
                    ),
                    "goal_difference": _coerce_float(match["predicted_home_goals"]) - _coerce_float(match["predicted_away_goals"]),
                    "goals_for": _coerce_float(match["predicted_home_goals"]),
                },
                {
                    "group_stage": match["stage"],
                    "team": match["away_team"],
                    "points": _points_for_outcome(
                        _coerce_float(match["predicted_away_goals"]),
                        _coerce_float(match["predicted_home_goals"]),
                    ),
                    "goal_difference": _coerce_float(match["predicted_away_goals"]) - _coerce_float(match["predicted_home_goals"]),
                    "goals_for": _coerce_float(match["predicted_away_goals"]),
                },
            ]
        )

    if not rows:
        return {}

    summary = pd.DataFrame(rows).groupby(["group_stage", "team"], as_index=False).sum(numeric_only=True)
    standings: dict[str, list[dict]] = {}
    for group_stage, frame in summary.groupby("group_stage", sort=True):
        ordered = frame.sort_values(
            ["points", "goal_difference", "goals_for", "team"],
            ascending=[False, False, False, True],
            kind="stable",
        ).reset_index(drop=True)
        standings[str(group_stage)] = ordered.to_dict("records")
    return standings



def _build_ranked_third_places(standings_by_group: dict[str, list[dict]]) -> list[dict]:
    rows: list[dict] = []
    for group_stage, records in standings_by_group.items():
        if len(records) < 3:
            continue
        row = dict(records[2])
        row["group_stage"] = group_stage
        row["group_letter"] = str(group_stage).split()[-1]
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            -float(row["points"]),
            -float(row["goal_difference"]),
            -float(row["goals_for"]),
            str(row["team"]),
        ),
    )



def _build_knockout_predictions(
    *,
    future_fixtures: pd.DataFrame,
    standings_by_group: dict[str, list[dict]],
    ranked_third_places: list[dict],
    team_context: dict[str, dict[str, float]],
) -> pd.DataFrame:
    if future_fixtures.empty:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)

    records: list[dict] = []
    winner_slots: dict[str, str] = {}
    loser_slots: dict[str, str] = {}
    used_third_place_groups: set[str] = set()
    stage_counts: dict[str, int] = {}

    fixtures = future_fixtures.sort_values(["match_date", "match_id"], kind="stable")
    for fixture in fixtures.to_dict("records"):
        stage = str(fixture["stage"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        slot_number = stage_counts[stage]
        home_team = _resolve_team_label(
            label=str(fixture["home_team"]),
            standings_by_group=standings_by_group,
            ranked_third_places=ranked_third_places,
            used_third_place_groups=used_third_place_groups,
            winner_slots=winner_slots,
            loser_slots=loser_slots,
        )
        away_team = _resolve_team_label(
            label=str(fixture["away_team"]),
            standings_by_group=standings_by_group,
            ranked_third_places=ranked_third_places,
            used_third_place_groups=used_third_place_groups,
            winner_slots=winner_slots,
            loser_slots=loser_slots,
        )
        record = _predict_match_record(
            fixture=fixture,
            home_team=home_team,
            away_team=away_team,
            team_context=team_context,
            knockout=True,
        )
        records.append(record)

        winner_key = f"{stage} {slot_number} Winner"
        loser_key = f"{stage} {slot_number} Loser"
        winner_slots[_normalize_slot_key(winner_key)] = str(record["predicted_winner"])
        loser_slots[_normalize_slot_key(loser_key)] = away_team if record["predicted_winner"] == home_team else home_team

    return pd.DataFrame(records, columns=PREDICTION_COLUMNS)



def _resolve_team_label(
    *,
    label: str,
    standings_by_group: dict[str, list[dict]],
    ranked_third_places: list[dict],
    used_third_place_groups: set[str],
    winner_slots: dict[str, str],
    loser_slots: dict[str, str],
) -> str:
    normalized_label = _normalize_slot_key(label)
    if normalized_label in winner_slots:
        return winner_slots[normalized_label]
    if normalized_label in loser_slots:
        return loser_slots[normalized_label]

    group_position_match = re.match(r"^Group ([A-L]) (Winner|2nd Place)$", label)
    if group_position_match:
        group_letter, position_label = group_position_match.groups()
        position_index = 0 if position_label == "Winner" else 1
        group_records = standings_by_group.get(f"Group {group_letter}", [])
        if len(group_records) > position_index:
            return str(group_records[position_index]["team"])
        return label

    third_place_match = re.match(r"^Third Place Group ([A-L](?:/[A-L])*)$", label)
    if third_place_match:
        allowed_groups = third_place_match.group(1).split("/")
        for row in ranked_third_places:
            group_letter = str(row["group_letter"])
            if group_letter not in allowed_groups or group_letter in used_third_place_groups:
                continue
            used_third_place_groups.add(group_letter)
            return str(row["team"])
    return label



def _normalize_slot_key(label: str) -> str:
    normalized = re.sub(r"\s+", " ", str(label).strip()).lower()
    normalized = normalized.replace("quarterfinals", "quarterfinal")
    normalized = normalized.replace("semifinals", "semifinal")
    return normalized



def _lookup_predicted_metric(
    frame: pd.DataFrame,
    is_home: bool,
    target_name: str,
) -> float | None:
    rows = frame.loc[
        (frame["is_home"] == is_home) & (frame["target_name"] == target_name)
    ]
    if rows.empty:
        return None
    value = rows["predicted_value"].iloc[0]
    if pd.isna(value):
        return None
    return float(value)



def _derive_winner(
    home_value: float | None,
    away_value: float | None,
    home_team: str,
    away_team: str,
) -> str | None:
    if home_value is None or away_value is None:
        return None
    if home_value > away_value:
        return home_team
    if away_value > home_value:
        return away_team
    return "Draw"



def _build_prediction_vs_actual(
    predictions: pd.DataFrame,
    observed_results: pd.DataFrame,
) -> pd.DataFrame:
    if predictions.empty or observed_results.empty:
        return pd.DataFrame(columns=MATCH_COMPARISON_COLUMNS)

    actuals = observed_results[
        [
            "match_id",
            "home_goals",
            "away_goals",
            "home_shots",
            "away_shots",
            "home_cards",
            "away_cards",
            "home_fouls",
            "away_fouls",
            "home_team",
            "away_team",
        ]
    ].copy()
    actuals["actual_winner"] = actuals.apply(
        lambda row: _derive_winner(
            _coerce_float(row["home_goals"]),
            _coerce_float(row["away_goals"]),
            row["home_team"],
            row["away_team"],
        ),
        axis=1,
    )
    merged = predictions.loc[~predictions["is_future_fixture"]].merge(
        actuals,
        on="match_id",
        how="left",
        suffixes=("", "_actual_context"),
    )
    merged["actual_home_goals"] = merged["home_goals"]
    merged["actual_away_goals"] = merged["away_goals"]
    merged["actual_home_shots"] = merged["home_shots"]
    merged["actual_away_shots"] = merged["away_shots"]
    merged["actual_home_cards"] = merged["home_cards"]
    merged["actual_away_cards"] = merged["away_cards"]
    merged["actual_home_fouls"] = merged["home_fouls"]
    merged["actual_away_fouls"] = merged["away_fouls"]
    merged["goal_error_home"] = (
        merged["predicted_home_goals"].astype(float) - merged["actual_home_goals"].astype(float)
    )
    merged["goal_error_away"] = (
        merged["predicted_away_goals"].astype(float) - merged["actual_away_goals"].astype(float)
    )
    merged["shot_error_home"] = (
        merged["predicted_home_shots"].astype(float) - merged["actual_home_shots"].astype(float)
    )
    merged["shot_error_away"] = (
        merged["predicted_away_shots"].astype(float) - merged["actual_away_shots"].astype(float)
    )
    merged["card_error_home"] = merged.apply(
        lambda row: _safe_metric_error(row.get("predicted_home_cards"), row.get("actual_home_cards")),
        axis=1,
    )
    merged["card_error_away"] = merged.apply(
        lambda row: _safe_metric_error(row.get("predicted_away_cards"), row.get("actual_away_cards")),
        axis=1,
    )
    merged["foul_error_home"] = merged.apply(
        lambda row: _safe_metric_error(row.get("predicted_home_fouls"), row.get("actual_home_fouls")),
        axis=1,
    )
    merged["foul_error_away"] = merged.apply(
        lambda row: _safe_metric_error(row.get("predicted_away_fouls"), row.get("actual_away_fouls")),
        axis=1,
    )
    merged["winner_hit"] = (
        merged["predicted_winner"] == merged["actual_winner"]
    ).astype(float)
    return merged[MATCH_COMPARISON_COLUMNS].sort_values(
        ["match_date", "match_id"],
        kind="stable",
    ).reset_index(drop=True)



def _build_group_forecast_summary(
    predictions: pd.DataFrame,
    observed_results: pd.DataFrame,
) -> pd.DataFrame:
    observed_group_rows = [
        row
        for row in _build_group_rows_from_actuals(observed_results)
        if str(row["group_stage"]).startswith("Group ")
    ]
    future_group_rows = [
        row
        for row in _build_group_rows_from_predictions(predictions)
        if str(row["group_stage"]).startswith("Group ")
    ]
    all_rows = observed_group_rows + future_group_rows
    if not all_rows:
        return pd.DataFrame(columns=GROUP_FORECAST_COLUMNS)

    summary = (
        pd.DataFrame(all_rows)
        .groupby(["group_stage", "team"], as_index=False)
        .sum(numeric_only=True)
    )
    summary["projected_total_points"] = (
        summary["observed_points"] + summary["projected_points"]
    )
    summary["projected_total_goal_difference"] = (
        summary["observed_goal_difference"] + summary["projected_goal_difference"]
    )
    return summary[GROUP_FORECAST_COLUMNS].sort_values(
        ["group_stage", "projected_total_points", "projected_total_goal_difference", "team"],
        ascending=[True, False, False, True],
        kind="stable",
    ).reset_index(drop=True)



def _build_group_rows_from_actuals(observed_results: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for match in observed_results.to_dict("records"):
        rows.extend(
            [
                {
                    "group_stage": match["stage"],
                    "team": match["home_team"],
                    "matches_played": 1.0,
                    "matches_remaining": 0.0,
                    "observed_points": _points_for_outcome(
                        _coerce_float(match["home_goals"]),
                        _coerce_float(match["away_goals"]),
                    ),
                    "projected_points": 0.0,
                    "observed_goal_difference": _coerce_float(match["home_goals"]) - _coerce_float(match["away_goals"]),
                    "projected_goal_difference": 0.0,
                },
                {
                    "group_stage": match["stage"],
                    "team": match["away_team"],
                    "matches_played": 1.0,
                    "matches_remaining": 0.0,
                    "observed_points": _points_for_outcome(
                        _coerce_float(match["away_goals"]),
                        _coerce_float(match["home_goals"]),
                    ),
                    "projected_points": 0.0,
                    "observed_goal_difference": _coerce_float(match["away_goals"]) - _coerce_float(match["home_goals"]),
                    "projected_goal_difference": 0.0,
                },
            ]
        )
    return rows



def _build_group_rows_from_predictions(predictions: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    group_predictions = predictions.loc[predictions["is_future_fixture"]].copy()
    for match in group_predictions.to_dict("records"):
        if not str(match["stage"]).startswith("Group "):
            continue
        home_goals = _coerce_float(match["predicted_home_goals"])
        away_goals = _coerce_float(match["predicted_away_goals"])
        rows.extend(
            [
                {
                    "group_stage": match["stage"],
                    "team": match["home_team"],
                    "matches_played": 0.0,
                    "matches_remaining": 1.0,
                    "observed_points": 0.0,
                    "projected_points": _points_for_outcome(home_goals, away_goals),
                    "observed_goal_difference": 0.0,
                    "projected_goal_difference": home_goals - away_goals,
                },
                {
                    "group_stage": match["stage"],
                    "team": match["away_team"],
                    "matches_played": 0.0,
                    "matches_remaining": 1.0,
                    "observed_points": 0.0,
                    "projected_points": _points_for_outcome(away_goals, home_goals),
                    "observed_goal_difference": 0.0,
                    "projected_goal_difference": away_goals - home_goals,
                },
            ]
        )
    return rows



def _points_for_outcome(goals_for: float, goals_against: float) -> float:
    if goals_for > goals_against:
        return 3.0
    if goals_for == goals_against:
        return 1.0
    return 0.0



def _coerce_float(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value)



def _safe_metric_error(predicted_value: object, actual_value: object) -> float | None:
    if predicted_value is None or actual_value is None or pd.isna(predicted_value) or pd.isna(actual_value):
        return None
    return float(predicted_value) - float(actual_value)



def _build_knockout_forecast_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame(columns=KNOCKOUT_FORECAST_COLUMNS)

    knockout = predictions.loc[
        predictions["is_future_fixture"] & ~predictions["stage"].astype(str).str.startswith("Group ")
    ].copy()
    if knockout.empty:
        return pd.DataFrame(columns=KNOCKOUT_FORECAST_COLUMNS)
    return knockout[KNOCKOUT_FORECAST_COLUMNS].sort_values(
        ["match_date", "match_id"],
        kind="stable",
    ).reset_index(drop=True)



def _build_team_forecast_summary(
    teams: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    observed = teams.rename(
        columns={
            "points": "observed_points",
            "goals_for": "observed_goals_for",
            "cards_for": "observed_cards_for",
            "fouls_for": "observed_fouls_for",
        }
    ).copy()
    if observed.empty:
        observed = pd.DataFrame(
            columns=[
                "team",
                "matches_played",
                "observed_points",
                "observed_goals_for",
                "observed_cards_for",
                "observed_fouls_for",
            ]
        )
    observed = observed[
        [
            "team",
            "matches_played",
            "observed_points",
            "observed_goals_for",
            "observed_cards_for",
            "observed_fouls_for",
        ]
    ]

    projected_rows: list[dict] = []
    future_group_predictions = predictions.loc[
        predictions["is_future_fixture"] & predictions["stage"].astype(str).str.startswith("Group ")
    ]
    for match in future_group_predictions.to_dict("records"):
        home_goals = _coerce_float(match["predicted_home_goals"])
        away_goals = _coerce_float(match["predicted_away_goals"])
        projected_rows.extend(
            [
                {
                    "team": match["home_team"],
                    "projected_points": _points_for_outcome(home_goals, away_goals),
                    "projected_goals_for": home_goals,
                    "projected_cards_for": _coerce_float(match.get("predicted_home_cards")),
                    "projected_fouls_for": _coerce_float(match.get("predicted_home_fouls")),
                },
                {
                    "team": match["away_team"],
                    "projected_points": _points_for_outcome(away_goals, home_goals),
                    "projected_goals_for": away_goals,
                    "projected_cards_for": _coerce_float(match.get("predicted_away_cards")),
                    "projected_fouls_for": _coerce_float(match.get("predicted_away_fouls")),
                },
            ]
        )
    projected = (
        pd.DataFrame(projected_rows)
        .groupby("team", as_index=False)
        .sum(numeric_only=True)
        if projected_rows
        else pd.DataFrame(
            columns=[
                "team",
                "projected_points",
                "projected_goals_for",
                "projected_cards_for",
                "projected_fouls_for",
            ]
        )
    )
    summary = observed.merge(projected, on="team", how="outer")
    for column in [
        "matches_played",
        "observed_points",
        "observed_goals_for",
        "observed_cards_for",
        "observed_fouls_for",
        "projected_points",
        "projected_goals_for",
        "projected_cards_for",
        "projected_fouls_for",
    ]:
        if column in summary.columns:
            summary[column] = pd.to_numeric(summary[column], errors="coerce").fillna(0.0)
    summary["forecast_total_points"] = (
        summary["observed_points"].astype(float) + summary["projected_points"].astype(float)
    )
    summary["forecast_total_goals_for"] = (
        summary["observed_goals_for"].astype(float) + summary["projected_goals_for"].astype(float)
    )
    summary["forecast_total_cards_for"] = (
        summary["observed_cards_for"].astype(float) + summary["projected_cards_for"].astype(float)
    )
    summary["forecast_total_fouls_for"] = (
        summary["observed_fouls_for"].astype(float) + summary["projected_fouls_for"].astype(float)
    )
    return summary[TEAM_FORECAST_COLUMNS].sort_values(
        ["forecast_total_points", "forecast_total_goals_for", "team"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)



def _build_title_probability_summary(
    *,
    team_priors: dict[str, dict[str, float]],
    team_forecast_summary: pd.DataFrame,
    knockout_forecast_summary: pd.DataFrame,
) -> pd.DataFrame:
    if team_forecast_summary.empty:
        return pd.DataFrame(columns=TITLE_PROBABILITY_COLUMNS)

    stage_weights = {
        "Round Of 32": 0.34,
        "Round Of 16": 0.48,
        "Quarterfinal": 0.62,
        "Quarterfinals": 0.62,
        "Semifinal": 0.79,
        "Semifinals": 0.79,
        "Third Place": 0.86,
        "3Rd Place Match": 0.86,
        "Final": 1.0,
    }
    projected_stage_lookup: dict[str, float] = {}
    for row in knockout_forecast_summary.to_dict("records"):
        stage_weight = stage_weights.get(str(row.get("stage")), 0.22)
        for team_name in (row.get("home_team"), row.get("away_team")):
            if team_name:
                projected_stage_lookup[str(team_name)] = max(
                    projected_stage_lookup.get(str(team_name), 0.22),
                    stage_weight,
                )

    rows: list[dict] = []
    for row in team_forecast_summary.to_dict("records"):
        team_name = str(row["team"])
        prior = _read_team_metrics(team_priors, team_name)
        projected_stage = projected_stage_lookup.get(team_name, 0.18)
        signal = max(
            0.01,
            prior["strength_rating"] * 0.55
            + float(row["forecast_total_points"]) * 8.0
            + float(row["forecast_total_goals_for"]) * 2.2
            + projected_stage * 20.0,
        )
        rows.append(
            {
                "team": team_name,
                "strength_rating": prior["strength_rating"],
                "projected_total_points": float(row["forecast_total_points"]),
                "projected_total_goals_for": float(row["forecast_total_goals_for"]),
                "projected_stage": projected_stage,
                "title_signal": signal,
            }
        )

    summary = pd.DataFrame(rows)
    summary["title_probability"] = summary["title_signal"].pow(4) / summary["title_signal"].pow(4).sum()
    summary["title_probability_pct"] = (summary["title_probability"] * 100.0).round(1)
    summary["final_probability_pct"] = (
        summary["title_probability"] * (0.65 + summary["projected_stage"] * 0.55) * 100.0
    ).round(1)
    summary["semifinal_probability_pct"] = (
        summary["title_probability"] * (0.95 + summary["projected_stage"] * 0.85) * 100.0
    ).round(1)
    return summary[TITLE_PROBABILITY_COLUMNS].sort_values(
        ["title_probability", "projected_total_points", "team"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)



def _build_top_scorer_forecast(
    *,
    roster_players: pd.DataFrame,
    team_forecast_summary: pd.DataFrame,
) -> pd.DataFrame:
    if roster_players.empty or team_forecast_summary.empty:
        return pd.DataFrame(columns=TOP_SCORER_COLUMNS)

    team_summary_lookup = team_forecast_summary.set_index("team").to_dict("index")
    ranked = roster_players.copy()
    ranked["current_goals"] = pd.to_numeric(ranked["total_goals"], errors="coerce").fillna(0.0)
    ranked["attack_signal"] = (
        ranked["current_goals"] * 1.0
        + pd.to_numeric(ranked["shots_on_target"], errors="coerce").fillna(0.0) * 0.35
        + pd.to_numeric(ranked["appearances"], errors="coerce").fillna(0.0) * 0.08
        + pd.to_numeric(ranked["sub_ins"], errors="coerce").fillna(0.0) * 0.03
    )
    total_by_team = ranked.groupby("team")["attack_signal"].transform("sum").replace(0.0, 1.0)
    ranked["goal_share_pct"] = (ranked["attack_signal"] / total_by_team) * 100.0

    projected_additional_goals: list[float] = []
    projected_total_goals: list[float] = []
    for row in ranked.to_dict("records"):
        team_summary = team_summary_lookup.get(str(row["team"]), {})
        remaining_team_goals = max(
            0.0,
            float(team_summary.get("forecast_total_goals_for", 0.0))
            - float(team_summary.get("observed_goals_for", 0.0)),
        )
        extra_goals = remaining_team_goals * float(row["goal_share_pct"]) / 100.0
        projected_additional_goals.append(extra_goals)
        projected_total_goals.append(float(row["current_goals"]) + extra_goals)

    ranked["projected_additional_goals"] = projected_additional_goals
    ranked["projected_total_goals"] = projected_total_goals
    ranked = ranked.sort_values(
        ["projected_total_goals", "current_goals", "team", "player_name"],
        ascending=[False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    return ranked[TOP_SCORER_COLUMNS].head(25)



def _build_methodology_status(
    coverage: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    target_lookup = {
        "goals": "goals_for",
        "shots": "shots_for",
        "cards": "cards_for",
        "fouls": "fouls_for",
    }
    rows: list[dict] = []
    for record in coverage.to_dict("records"):
        target_name = target_lookup[record["metric_name"]]
        prediction_column = {
            "goals_for": "predicted_home_goals",
            "shots_for": "predicted_home_shots",
            "cards_for": "predicted_home_cards",
            "fouls_for": "predicted_home_fouls",
        }[target_name]
        has_predictions = bool(
            prediction_column in predictions.columns
            and not predictions[prediction_column].dropna().empty
        )
        if record["has_truth"] and has_predictions:
            publish_status = "published"
        elif has_predictions:
            publish_status = "forecast-only"
        elif record["has_truth"]:
            publish_status = "truth-only"
        else:
            publish_status = "truth-unavailable"
        rows.append(
            {
                "metric_name": record["metric_name"],
                "has_truth": bool(record["has_truth"]),
                "truth_coverage_pct": float(record["coverage_pct"]),
                "has_predictions": bool(has_predictions),
                "publish_status": publish_status,
            }
        )
    return pd.DataFrame(rows, columns=METHODOLOGY_STATUS_COLUMNS)



def _build_coverage_summary(observed_results: pd.DataFrame) -> pd.DataFrame:
    total_matches = len(observed_results.index)
    shots_covered = 0
    cards_covered = 0
    fouls_covered = 0
    if not observed_results.empty and {"home_shots", "away_shots"}.issubset(observed_results.columns):
        shots_covered = int(
            (
                observed_results["home_shots"].notna()
                & observed_results["away_shots"].notna()
            ).sum()
        )
    if not observed_results.empty and {"home_cards", "away_cards"}.issubset(observed_results.columns):
        cards_covered = int(
            (
                observed_results["home_cards"].notna()
                & observed_results["away_cards"].notna()
            ).sum()
        )
    if not observed_results.empty and {"home_fouls", "away_fouls"}.issubset(observed_results.columns):
        fouls_covered = int(
            (
                observed_results["home_fouls"].notna()
                & observed_results["away_fouls"].notna()
            ).sum()
        )
    rows = []
    for metric_name, covered_matches in (
        ("goals", total_matches),
        ("cards", cards_covered),
        ("fouls", fouls_covered),
        ("shots", shots_covered),
    ):
        coverage_pct = 0.0 if total_matches == 0 else (covered_matches / total_matches) * 100.0
        rows.append(
            {
                "metric_name": metric_name,
                "covered_matches": covered_matches,
                "total_matches": total_matches,
                "coverage_pct": coverage_pct,
                "has_truth": covered_matches > 0,
            }
        )
    return pd.DataFrame(rows)



def _build_team_summary(observed_results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for match in observed_results.to_dict("records"):
        rows.append(
            {
                "team": match["home_team"],
                "goals_for": match["home_goals"],
                "goals_against": match["away_goals"],
                "shots_for": match.get("home_shots") or 0,
                "cards_for": match.get("home_cards") or 0,
                "fouls_for": match.get("home_fouls") or 0,
                "wins": 1 if match["home_goals"] > match["away_goals"] else 0,
                "draws": 1 if match["home_goals"] == match["away_goals"] else 0,
                "losses": 1 if match["home_goals"] < match["away_goals"] else 0,
                "points": 3 if match["home_goals"] > match["away_goals"] else 1 if match["home_goals"] == match["away_goals"] else 0,
            }
        )
        rows.append(
            {
                "team": match["away_team"],
                "goals_for": match["away_goals"],
                "goals_against": match["home_goals"],
                "shots_for": match.get("away_shots") or 0,
                "cards_for": match.get("away_cards") or 0,
                "fouls_for": match.get("away_fouls") or 0,
                "wins": 1 if match["away_goals"] > match["home_goals"] else 0,
                "draws": 1 if match["away_goals"] == match["home_goals"] else 0,
                "losses": 1 if match["away_goals"] < match["home_goals"] else 0,
                "points": 3 if match["away_goals"] > match["home_goals"] else 1 if match["away_goals"] == match["home_goals"] else 0,
            }
        )

    if not rows:
        return pd.DataFrame(columns=TEAM_SUMMARY_COLUMNS)

    summary = (
        pd.DataFrame(rows)
        .groupby("team", as_index=False)
        .sum()
        .assign(
            matches_played=lambda frame: frame["wins"] + frame["draws"] + frame["losses"],
            goal_difference=lambda frame: frame["goals_for"] - frame["goals_against"],
        )
    )
    return summary[TEAM_SUMMARY_COLUMNS].sort_values(
        ["points", "goal_difference", "goals_for", "team"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)



