from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Iterable

import pandas as pd

from src.config import API_FOOTBALL_PRIOR_SEASON, has_api_football_credentials
from src.domain.match_schema import PublicMatchTruthRow
from src.evaluation.run_backtest import run_backtest
from src.ingestion.api_football_client import APIFootballClient
from src.ingestion.espn_client import ESPNClient
from src.ingestion.espn_roster_client import ESPNRosterClient
from src.ingestion.fifa_client import FIFAClient
from src.ingestion.lineup_client import LineupClient
from src.features.team_match_features import build_team_match_features
from src.serving.load_outputs import write_serving_outputs
from src.tournament_predictor import calculate_composite_strength

PUBLIC_MATCH_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "home_shots",
    "away_shots",
    "home_cards",
    "away_cards",
    "home_fouls",
    "away_fouls",
    "status",
    "source",
    "source_retrieved_at",
    "is_future_fixture",
    "home_lineup_confirmed",
    "away_lineup_confirmed",
    "home_probable_lineup_count",
    "away_probable_lineup_count",
    "home_substitutions_used",
    "away_substitutions_used",
]

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
TOP_SCORER_COLUMNS = [
    "player_name",
    "team",
    "position",
    "current_goals",
    "goal_share_pct",
    "projected_additional_goals",
    "projected_total_goals",
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
TOURNAMENT_FINAL_DATE = "2026-07-19"


def build_real_serving_snapshot(
    start_date: str,
    end_date: str,
    output_dir: Path,
    client: ESPNClient | None = None,
    schedule_client: object | None = None,
    lineup_client: LineupClient | None = None,
    roster_client: ESPNRosterClient | None = None,
    api_football_client: APIFootballClient | None = None,
    disable_ssl_verification: bool = False,
    forecast_end_date: str | None = None,
) -> dict[str, pd.DataFrame]:
    normalized_matches = _load_normalized_matches(
        start_date=start_date,
        end_date=end_date,
        client=client,
        disable_ssl_verification=disable_ssl_verification,
    )
    if schedule_client is None:
        schedule_client = ESPNClient(verify_ssl=not disable_ssl_verification)
    future_fixture_rows = _load_future_fixtures(
        start_date=start_date,
        end_date=forecast_end_date or TOURNAMENT_FINAL_DATE,
        schedule_client=schedule_client,
    )

    observed_results = _build_public_match_frame(normalized_matches, is_future_fixture=False)
    future_fixtures = _build_public_match_frame(future_fixture_rows, is_future_fixture=True)
    if lineup_client is not None:
        observed_results = _attach_player_context(observed_results, lineup_client)
        future_fixtures = _attach_player_context(future_fixtures, lineup_client)
    coverage = _build_coverage_summary(observed_results)
    teams = _build_team_summary(observed_results)
    if roster_client is None and _rows_have_team_ids(normalized_matches + future_fixture_rows):
        roster_client = ESPNRosterClient(verify_ssl=not disable_ssl_verification)
    if api_football_client is None and has_api_football_credentials():
        api_football_client = APIFootballClient()
    team_priors, roster_players = _build_team_priors(
        match_rows=normalized_matches + future_fixture_rows,
        observed_results=observed_results,
        future_fixtures=future_fixtures,
        roster_client=roster_client,
        api_football_client=api_football_client,
    )
    team_match_history = _build_team_match_history(observed_results, future_fixtures, team_priors)
    featured_history = build_team_match_features(team_match_history)
    observed_feature_table = _build_target_feature_table(
        featured_history.loc[~featured_history["is_future_fixture"]].copy()
    )
    backtest_outputs = run_backtest(observed_feature_table)
    observed_side_predictions = _merge_prediction_context(
        backtest_outputs["predictions"],
        observed_feature_table,
    )
    observed_predictions = _build_public_match_predictions(observed_side_predictions)
    future_predictions = _build_future_match_predictions(
        future_fixtures=future_fixtures,
        observed_results=observed_results,
        team_priors=team_priors,
    )
    predictions = _combine_match_predictions(
        observed_predictions,
        future_predictions,
    )
    match_prediction_vs_actual = _build_prediction_vs_actual(predictions, observed_results)
    group_forecast_summary = _build_group_forecast_summary(
        predictions,
        observed_results,
    )
    knockout_forecast_summary = _build_knockout_forecast_summary(predictions)
    team_forecast_summary = _build_team_forecast_summary(teams, predictions)
    title_probability_summary = _build_title_probability_summary(
        team_priors=team_priors,
        team_forecast_summary=team_forecast_summary,
        knockout_forecast_summary=knockout_forecast_summary,
    )
    top_scorer_forecast = _build_top_scorer_forecast(
        roster_players=roster_players,
        team_forecast_summary=team_forecast_summary,
    )
    methodology_status = _build_methodology_status(coverage, predictions)

    write_serving_outputs(
        output_dir,
        leaderboard=backtest_outputs["leaderboard"],
        predictions=predictions,
        teams=teams,
        coverage_summary=coverage,
        observed_match_results=observed_results,
        match_prediction_vs_actual=match_prediction_vs_actual,
        group_forecast_summary=group_forecast_summary,
        knockout_forecast_summary=knockout_forecast_summary,
        team_forecast_summary=team_forecast_summary,
        methodology_status=methodology_status,
        title_probability_summary=title_probability_summary,
        top_scorer_forecast=top_scorer_forecast,
    )
    return {
        "observed_results": observed_results,
        "future_fixtures": future_fixtures,
        "coverage": coverage,
        "teams": teams,
        "leaderboard": backtest_outputs["leaderboard"],
        "predictions": predictions,
        "match_prediction_vs_actual": match_prediction_vs_actual,
        "group_forecast_summary": group_forecast_summary,
        "knockout_forecast_summary": knockout_forecast_summary,
        "team_forecast_summary": team_forecast_summary,
        "methodology_status": methodology_status,
        "title_probability_summary": title_probability_summary,
        "top_scorer_forecast": top_scorer_forecast,
    }


def _load_normalized_matches(
    start_date: str,
    end_date: str,
    client: ESPNClient | None,
    disable_ssl_verification: bool,
) -> list[dict]:
    if client is not None:
        return _fetch_completed_matches(client, start_date, end_date)

    fifa_matches = _fetch_fifa_matches(start_date, end_date)
    if fifa_matches:
        return fifa_matches

    espn_client = ESPNClient(verify_ssl=not disable_ssl_verification)
    return _fetch_completed_matches(espn_client, start_date, end_date)


def _load_future_fixtures(
    start_date: str,
    end_date: str,
    schedule_client: object | None,
) -> list[dict]:
    if schedule_client is None:
        return []

    rows: list[dict] = []
    for match_date in _iter_dates(start_date, end_date):
        rows.extend(schedule_client.fetch_matches_for_date(match_date))
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows


def _fetch_completed_matches(client: ESPNClient, start_date: str, end_date: str) -> list[dict]:
    rows: list[dict] = []
    for match_date in _iter_dates(start_date, end_date):
        rows.extend(client.fetch_completed_matches_for_date(match_date))
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows


def _iter_dates(start_date: str, end_date: str) -> Iterable[date]:
    current = _parse_date(start_date)
    finish = _parse_date(end_date)
    while current <= finish:
        yield current
        current += timedelta(days=1)


def _fetch_fifa_matches(start_date: str, end_date: str) -> list[dict]:
    try:
        raw_matches = FIFAClient().fetch_world_cup_matches()
    except Exception:
        return []

    start = _parse_date(start_date)
    finish = _parse_date(end_date)
    rows: list[dict] = []
    for raw_match in raw_matches:
        match_day = _parse_date(str(raw_match.get("date", ""))[:10])
        if match_day < start or match_day > finish:
            continue
        rows.append(
            {
                "match_id": raw_match["id"],
                "match_date": raw_match["date"],
                "stage": raw_match["stage"],
                "home_team": raw_match["home_team"]["name"],
                "away_team": raw_match["away_team"]["name"],
                "home_goals": raw_match["home_team"]["goals"],
                "away_goals": raw_match["away_team"]["goals"],
                "home_shots": raw_match["home_team"].get("shots"),
                "away_shots": raw_match["away_team"].get("shots"),
                "home_cards": raw_match["home_team"].get("cards"),
                "away_cards": raw_match["away_team"].get("cards"),
                "home_fouls": raw_match["home_team"].get("fouls"),
                "away_fouls": raw_match["away_team"].get("fouls"),
                "status": "Final",
                "source": raw_match.get("source", "fifa"),
                "source_retrieved_at": raw_match.get("retrieved_at"),
            }
        )
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows


def _build_public_match_frame(rows: list[dict], is_future_fixture: bool) -> pd.DataFrame:
    normalized_rows = []
    allowed_keys = set(PUBLIC_MATCH_COLUMNS)
    for row in rows:
        payload = {key: value for key, value in dict(row).items() if key in allowed_keys}
        payload.setdefault("is_future_fixture", is_future_fixture)
        normalized_rows.append(
            PublicMatchTruthRow(**payload).model_dump()
        )
    return pd.DataFrame(normalized_rows, columns=PUBLIC_MATCH_COLUMNS)


def _attach_player_context(frame: pd.DataFrame, lineup_client: LineupClient) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    context_rows = []
    for match_id in frame["match_id"].astype(str):
        context = lineup_client.fetch_match_player_context(match_id)
        context_rows.append({"match_id": match_id, **context})

    context_frame = pd.DataFrame(
        context_rows,
        columns=[
            "match_id",
            "home_lineup_confirmed",
            "away_lineup_confirmed",
            "home_probable_lineup_count",
            "away_probable_lineup_count",
            "home_substitutions_used",
            "away_substitutions_used",
        ],
    )
    merged = frame.copy()
    merged["match_id"] = merged["match_id"].astype(str)
    merged = merged.drop(
        columns=[
            "home_lineup_confirmed",
            "away_lineup_confirmed",
            "home_probable_lineup_count",
            "away_probable_lineup_count",
            "home_substitutions_used",
            "away_substitutions_used",
        ]
    ).merge(context_frame, on="match_id", how="left")
    return merged[PUBLIC_MATCH_COLUMNS]


def _rows_have_team_ids(rows: list[dict]) -> bool:
    for row in rows:
        if row.get("home_team_id") or row.get("away_team_id"):
            return True
    return False


def _normalize_team_name(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    aliases = {
        "bosnia herzegovina": "bosnia herzegovina",
        "cape verde": "cape verde",
        "congo dr": "congo dr",
        "czech republic": "czechia",
        "czechia": "czechia",
        "curacao": "curacao",
        "ivory coast": "ivory coast",
        "korea republic": "south korea",
        "korea south": "south korea",
        "mexico": "mexico",
        "morocco": "morocco",
        "netherlands": "netherlands",
        "saudi arabia": "saudi arabia",
        "south korea": "south korea",
        "turkey": "turkiye",
        "turkiye": "turkiye",
        "united states": "united states",
        "usa": "united states",
    }
    return aliases.get(text, text)


def _build_team_priors(
    *,
    match_rows: list[dict],
    observed_results: pd.DataFrame,
    future_fixtures: pd.DataFrame,
    roster_client: ESPNRosterClient | None,
    api_football_client: APIFootballClient | None,
) -> tuple[dict[str, dict[str, float]], pd.DataFrame]:
    teams = sorted(
        {
            str(team)
            for frame in (observed_results, future_fixtures)
            if not frame.empty
            for column in ("home_team", "away_team")
            for team in frame[column].dropna().tolist()
        }
    )
    if not teams:
        return {"_defaults": _default_prior_metrics()}, pd.DataFrame(columns=TOP_SCORER_COLUMNS)

    team_id_lookup: dict[str, str] = {}
    for row in match_rows:
        for team_key, id_key in (("home_team", "home_team_id"), ("away_team", "away_team_id")):
            team_name = row.get(team_key)
            team_id = row.get(id_key)
            if team_name and team_id:
                team_id_lookup[str(team_name)] = str(team_id)

    components = _load_team_strength_components()
    roster_players = _load_roster_players(team_id_lookup, roster_client)
    api_football_players = _load_api_football_players(teams, api_football_client)
    roster_players = _combine_player_sources(roster_players, api_football_players)
    roster_summary = _build_roster_team_summary(roster_players)

    prior_rows: list[dict] = []
    for team_name in teams:
        component_row = _match_strength_row(components, team_name)
        roster_row = _match_roster_row(roster_summary, team_name)
        prior_rows.append(_build_team_prior_row(team_name, component_row, roster_row))

    priors_frame = pd.DataFrame(prior_rows)
    defaults = {
        "goals_for_avg": float(priors_frame["goals_for_avg"].mean() or 1.25),
        "goals_against_avg": float(priors_frame["goals_against_avg"].mean() or 1.25),
        "shots_for_avg": float(priors_frame["shots_for_avg"].mean() or 10.5),
        "cards_for_avg": float(priors_frame["cards_for_avg"].mean() or 1.9),
        "fouls_for_avg": float(priors_frame["fouls_for_avg"].mean() or 11.0),
        "points_per_match": float(priors_frame["points_per_match"].mean() or 1.3),
        "goal_diff_per_match": float(priors_frame["goal_diff_per_match"].mean() or 0.0),
        "strength_rating": float(priors_frame["strength_rating"].mean() or 75.0),
    }
    lookup = {
        str(row["team"]): {
            "goals_for_avg": float(row["goals_for_avg"]),
            "goals_against_avg": float(row["goals_against_avg"]),
            "shots_for_avg": float(row["shots_for_avg"]),
            "cards_for_avg": float(row["cards_for_avg"]),
            "fouls_for_avg": float(row["fouls_for_avg"]),
            "points_per_match": float(row["points_per_match"]),
            "goal_diff_per_match": float(row["goal_diff_per_match"]),
            "strength_rating": float(row["strength_rating"]),
        }
        for row in prior_rows
    }
    lookup["_defaults"] = defaults
    return lookup, roster_players


def _default_prior_metrics() -> dict[str, float]:
    return {
        "goals_for_avg": 1.25,
        "goals_against_avg": 1.25,
        "shots_for_avg": 10.5,
        "cards_for_avg": 1.9,
        "fouls_for_avg": 11.0,
        "points_per_match": 1.3,
        "goal_diff_per_match": 0.0,
        "strength_rating": 75.0,
    }


def _load_team_strength_components() -> pd.DataFrame:
    path = Path(__file__).resolve().parents[2] / "data" / "reference" / "team_strength_components.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame = calculate_composite_strength(frame)
    frame["team_key"] = frame["team"].map(_normalize_team_name)
    return frame


def _load_roster_players(
    team_id_lookup: dict[str, str],
    roster_client: ESPNRosterClient | None,
) -> pd.DataFrame:
    if roster_client is None or not team_id_lookup:
        return pd.DataFrame()

    rows: list[dict] = []
    for team_name, team_id in sorted(team_id_lookup.items()):
        try:
            rows.extend(roster_client.fetch_team_roster(team_id, team_name=team_name))
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame["team_key"] = frame["team"].map(_normalize_team_name)
    return frame


def _load_api_football_players(
    teams: list[str],
    api_football_client: APIFootballClient | None,
) -> pd.DataFrame:
    if api_football_client is None or not teams:
        return pd.DataFrame()

    rows: list[dict] = []
    for team_name in teams:
        try:
            team_payload = api_football_client.search_team(team_name)
        except Exception:
            continue
        if not team_payload or not team_payload.get("id"):
            continue
        try:
            rows.extend(
                api_football_client.fetch_team_recent_player_stats(
                    team_payload["id"],
                    season=API_FOOTBALL_PRIOR_SEASON,
                    team_name=team_name,
                )
            )
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame["team_key"] = frame["team"].map(_normalize_team_name)
    return frame


def _combine_player_sources(
    espn_players: pd.DataFrame,
    api_football_players: pd.DataFrame,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if not espn_players.empty:
        espn = espn_players.copy()
        espn["source"] = espn.get("source", "espn")
        frames.append(espn)
    if not api_football_players.empty:
        api_players = api_football_players.copy()
        api_players["source"] = api_players.get("source", "api-football")
        frames.append(api_players)
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["player_key"] = combined["player_name"].map(_normalize_team_name)
    combined["source_priority"] = combined["source"].map({"espn": 1, "api-football": 2}).fillna(0)
    combined = combined.sort_values(
        ["team_key", "player_key", "source_priority"],
        ascending=[True, True, False],
        kind="stable",
    )
    combined = combined.drop_duplicates(["team_key", "player_key"], keep="first")
    return combined.drop(columns=["player_key", "source_priority"], errors="ignore").reset_index(drop=True)


def _build_roster_team_summary(roster_players: pd.DataFrame) -> pd.DataFrame:
    if roster_players.empty:
        return pd.DataFrame()

    grouped = roster_players.groupby(["team", "team_key"], as_index=False).agg(
        appearances=("appearances", "sum"),
        sub_ins=("sub_ins", "sum"),
        total_goals=("total_goals", "sum"),
        total_shots=("total_shots", "sum"),
        shots_on_target=("shots_on_target", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
        fouls_committed=("fouls_committed", "sum"),
    )
    estimated_matches = (grouped["appearances"] / 11.0).clip(lower=1.0)
    grouped["roster_goals_per_match"] = grouped["total_goals"] / estimated_matches
    grouped["roster_shots_per_match"] = grouped["total_shots"] / estimated_matches
    grouped["roster_cards_per_match"] = (
        grouped["yellow_cards"] + grouped["red_cards"] * 2.0
    ) / estimated_matches
    grouped["roster_fouls_per_match"] = grouped["fouls_committed"] / estimated_matches
    return grouped


def _match_strength_row(components: pd.DataFrame, team_name: str) -> dict | None:
    if components.empty:
        return None
    matches = components.loc[components["team_key"] == _normalize_team_name(team_name)]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _match_roster_row(roster_summary: pd.DataFrame, team_name: str) -> dict | None:
    if roster_summary.empty:
        return None
    matches = roster_summary.loc[roster_summary["team_key"] == _normalize_team_name(team_name)]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _build_team_prior_row(team_name: str, component_row: dict | None, roster_row: dict | None) -> dict:
    attack_score = float((component_row or {}).get("attack_score", 72.0))
    defense_score = float((component_row or {}).get("defense_score", 72.0))
    recent_form_score = float((component_row or {}).get("recent_form_score", 70.0))
    confidence_score = float((component_row or {}).get("confidence_score", 0.65))
    strength_rating = float((component_row or {}).get("adjusted_strength", 74.0))

    strength_goals = 0.55 + attack_score * 0.012 + recent_form_score * 0.004
    strength_shots = 4.5 + attack_score * 0.08 + defense_score * 0.015
    strength_cards = 1.1 + max(0.0, (78.0 - confidence_score * 100.0)) * 0.02
    strength_fouls = 8.0 + max(0.0, (80.0 - confidence_score * 100.0)) * 0.08

    roster_goals = float((roster_row or {}).get("roster_goals_per_match", 0.0))
    roster_shots = float((roster_row or {}).get("roster_shots_per_match", 0.0))
    roster_cards = float((roster_row or {}).get("roster_cards_per_match", 0.0))
    roster_fouls = float((roster_row or {}).get("roster_fouls_per_match", 0.0))
    roster_available = roster_row is not None and (
        roster_goals > 0 or roster_shots > 0 or roster_cards > 0 or roster_fouls > 0
    )

    goals_for_avg = _blend_prior_values(strength_goals, roster_goals, roster_available, 0.42)
    shots_for_avg = _blend_prior_values(strength_shots, roster_shots, roster_available, 0.42)
    cards_for_avg = _blend_prior_values(strength_cards, roster_cards, roster_available, 0.5)
    fouls_for_avg = _blend_prior_values(strength_fouls, roster_fouls, roster_available, 0.5)
    goals_against_avg = max(0.55, 2.2 - defense_score * 0.013 - confidence_score * 0.2)
    points_per_match = min(2.6, 0.55 + strength_rating * 0.019)
    goal_diff_per_match = goals_for_avg - goals_against_avg

    return {
        "team": team_name,
        "strength_rating": round(strength_rating, 2),
        "goals_for_avg": round(goals_for_avg, 2),
        "goals_against_avg": round(goals_against_avg, 2),
        "shots_for_avg": round(shots_for_avg, 2),
        "cards_for_avg": round(cards_for_avg, 2),
        "fouls_for_avg": round(fouls_for_avg, 2),
        "points_per_match": round(points_per_match, 2),
        "goal_diff_per_match": round(goal_diff_per_match, 2),
    }


def _blend_prior_values(
    strength_value: float,
    roster_value: float,
    roster_available: bool,
    roster_weight: float,
) -> float:
    if not roster_available:
        return strength_value
    return strength_value * (1.0 - roster_weight) + roster_value * roster_weight


def _build_team_match_history(
    observed_results: pd.DataFrame,
    future_fixtures: pd.DataFrame,
    team_priors: dict[str, dict[str, float]],
) -> pd.DataFrame:
    rows: list[dict] = []
    for match in observed_results.to_dict("records"):
        rows.extend(_build_team_side_rows(match, is_future_fixture=False, team_priors=team_priors))
    for match in future_fixtures.to_dict("records"):
        rows.extend(_build_team_side_rows(match, is_future_fixture=True, team_priors=team_priors))

    history_columns = [
        "match_id",
        "match_date",
        "stage",
        "status",
        "source",
        "is_future_fixture",
        "home_team",
        "away_team",
        "team",
        "opponent",
        "is_home",
        "goals_for",
        "shots_for",
        "cards_for",
        "fouls_for",
        "has_cards_truth",
        "has_fouls_truth",
        "home_lineup_confirmed",
        "away_lineup_confirmed",
        "home_probable_lineup_count",
        "away_probable_lineup_count",
        "home_substitutions_used",
        "away_substitutions_used",
        "lineup_confirmed_flag",
        "probable_lineup_count",
        "substitutions_used",
        "team_goals_prior",
        "team_shots_prior",
        "team_cards_prior",
        "team_fouls_prior",
    ]
    return pd.DataFrame(rows, columns=history_columns)


def _build_team_side_rows(
    match: dict,
    *,
    is_future_fixture: bool,
    team_priors: dict[str, dict[str, float]],
) -> list[dict]:
    def _metric_value(key: str) -> float:
        value = match.get(key)
        if value is None or pd.isna(value):
            return 0.0
        return float(value)

    home_team = str(match["home_team"])
    away_team = str(match["away_team"])
    home_prior = _read_team_metrics(team_priors, home_team)
    away_prior = _read_team_metrics(team_priors, away_team)

    return [
        {
            "match_id": str(match["match_id"]),
            "match_date": match["match_date"],
            "stage": match["stage"],
            "status": match["status"],
            "source": match.get("source", ""),
            "is_future_fixture": is_future_fixture,
            "home_team": home_team,
            "away_team": away_team,
            "team": home_team,
            "opponent": away_team,
            "is_home": True,
            "goals_for": _metric_value("home_goals"),
            "shots_for": _metric_value("home_shots"),
            "cards_for": _metric_value("home_cards"),
            "fouls_for": _metric_value("home_fouls"),
            "has_cards_truth": pd.notna(match.get("home_cards")),
            "has_fouls_truth": pd.notna(match.get("home_fouls")),
            "home_lineup_confirmed": bool(match.get("home_lineup_confirmed", False)),
            "away_lineup_confirmed": bool(match.get("away_lineup_confirmed", False)),
            "home_probable_lineup_count": int(match.get("home_probable_lineup_count", 0) or 0),
            "away_probable_lineup_count": int(match.get("away_probable_lineup_count", 0) or 0),
            "home_substitutions_used": int(match.get("home_substitutions_used", 0) or 0),
            "away_substitutions_used": int(match.get("away_substitutions_used", 0) or 0),
            "lineup_confirmed_flag": bool(match.get("home_lineup_confirmed", False)),
            "probable_lineup_count": int(match.get("home_probable_lineup_count", 0) or 0),
            "substitutions_used": int(match.get("home_substitutions_used", 0) or 0),
            "team_goals_prior": home_prior["goals_for_avg"],
            "team_shots_prior": home_prior["shots_for_avg"],
            "team_cards_prior": home_prior["cards_for_avg"],
            "team_fouls_prior": home_prior["fouls_for_avg"],
        },
        {
            "match_id": str(match["match_id"]),
            "match_date": match["match_date"],
            "stage": match["stage"],
            "status": match["status"],
            "source": match.get("source", ""),
            "is_future_fixture": is_future_fixture,
            "home_team": home_team,
            "away_team": away_team,
            "team": away_team,
            "opponent": home_team,
            "is_home": False,
            "goals_for": _metric_value("away_goals"),
            "shots_for": _metric_value("away_shots"),
            "cards_for": _metric_value("away_cards"),
            "fouls_for": _metric_value("away_fouls"),
            "has_cards_truth": pd.notna(match.get("away_cards")),
            "has_fouls_truth": pd.notna(match.get("away_fouls")),
            "home_lineup_confirmed": bool(match.get("home_lineup_confirmed", False)),
            "away_lineup_confirmed": bool(match.get("away_lineup_confirmed", False)),
            "home_probable_lineup_count": int(match.get("home_probable_lineup_count", 0) or 0),
            "away_probable_lineup_count": int(match.get("away_probable_lineup_count", 0) or 0),
            "home_substitutions_used": int(match.get("home_substitutions_used", 0) or 0),
            "away_substitutions_used": int(match.get("away_substitutions_used", 0) or 0),
            "lineup_confirmed_flag": bool(match.get("away_lineup_confirmed", False)),
            "probable_lineup_count": int(match.get("away_probable_lineup_count", 0) or 0),
            "substitutions_used": int(match.get("away_substitutions_used", 0) or 0),
            "team_goals_prior": away_prior["goals_for_avg"],
            "team_shots_prior": away_prior["shots_for_avg"],
            "team_cards_prior": away_prior["cards_for_avg"],
            "team_fouls_prior": away_prior["fouls_for_avg"],
        },
    ]


def _build_target_feature_table(team_match_history: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    target_specs = [
        ("goals_for", "goals_for"),
        ("shots_for", "shots_for"),
        ("cards_for", "cards_for"),
        ("fouls_for", "fouls_for"),
    ]
    for match in team_match_history.to_dict("records"):
        for target_name, value_column in target_specs:
            row = {
                "match_id": match["match_id"],
                "match_date": match["match_date"],
                "stage": match["stage"],
                "status": match["status"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "team": match["team"],
                "is_home": bool(match["is_home"]),
                "is_future_fixture": bool(match["is_future_fixture"]),
                "target_name": target_name,
                "actual_value": float(match[value_column]),
                "has_cards_truth": bool(match["has_cards_truth"]),
                "has_fouls_truth": bool(match["has_fouls_truth"]),
                "team_goals_avg_last_3": float(match.get("team_goals_avg_last_3", 0.0)),
                "team_shots_avg_last_3": float(match.get("team_shots_avg_last_3", 0.0)),
                "team_cards_avg_last_3": float(match.get("team_cards_avg_last_3", 0.0)),
                "team_fouls_avg_last_3": float(match.get("team_fouls_avg_last_3", 0.0)),
                "hybrid_goals_signal": float(match.get("hybrid_goals_signal", 0.0)),
                "hybrid_shots_signal": float(match.get("hybrid_shots_signal", 0.0)),
                "hybrid_cards_signal": float(match.get("hybrid_cards_signal", 0.0)),
                "hybrid_fouls_signal": float(match.get("hybrid_fouls_signal", 0.0)),
                "lineup_confirmed_flag": float(match.get("lineup_confirmed_flag", 0.0)),
                "probable_lineup_completeness": float(match.get("probable_lineup_completeness", 0.0)),
                "bench_usage_rate": float(match.get("bench_usage_rate", 0.0)),
            }
            if target_name == "cards_for" and not row["has_cards_truth"]:
                continue
            if target_name == "fouls_for" and not row["has_fouls_truth"]:
                continue
            rows.append(row)

    feature_columns = [
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
        "actual_value",
        "has_cards_truth",
        "has_fouls_truth",
        "team_goals_avg_last_3",
        "team_shots_avg_last_3",
        "team_cards_avg_last_3",
        "team_fouls_avg_last_3",
        "hybrid_goals_signal",
        "hybrid_shots_signal",
        "hybrid_cards_signal",
        "hybrid_fouls_signal",
        "lineup_confirmed_flag",
        "probable_lineup_completeness",
        "bench_usage_rate",
    ]
    return pd.DataFrame(rows, columns=feature_columns)


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


def _read_team_metrics(
    team_context: dict[str, dict[str, float]],
    team_name: str,
) -> dict[str, float]:
    defaults = team_context.get("_defaults", {})
    metrics = defaults.copy()
    metrics.update(team_context.get(team_name, {}))
    return metrics


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


def _coerce_float(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def _safe_metric_error(predicted_value: object, actual_value: object) -> float | None:
    if predicted_value is None or actual_value is None or pd.isna(predicted_value) or pd.isna(actual_value):
        return None
    return float(predicted_value) - float(actual_value)


def _points_for_outcome(goals_for: float, goals_against: float) -> float:
    if goals_for > goals_against:
        return 3.0
    if goals_for == goals_against:
        return 1.0
    return 0.0


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build real serving snapshot artifacts from ESPN scoreboard data.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--forecast-end-date", default=TOURNAMENT_FINAL_DATE)
    parser.add_argument("--output-dir", default=str(Path("data/serving")))
    parser.add_argument("--disable-ssl-verification", action="store_true")
    args = parser.parse_args()

    build_real_serving_snapshot(
        start_date=args.start_date,
        end_date=args.end_date,
        forecast_end_date=args.forecast_end_date,
        output_dir=Path(args.output_dir),
        disable_ssl_verification=args.disable_ssl_verification,
    )


if __name__ == "__main__":
    main()
