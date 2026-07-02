from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

from src.config import API_FOOTBALL_PRIOR_SEASON
from src.tournament_predictor import calculate_composite_strength
from src.ingestion.espn_roster_client import ESPNRosterClient
from src.ingestion.api_football_client import APIFootballClient
from src.pipelines.ingest_sources import _normalize_team_name

TOP_SCORER_COLUMNS = [
    "player_name",
    "team",
    "position",
    "current_goals",
    "goal_share_pct",
    "projected_additional_goals",
    "projected_total_goals",
]

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



def _read_team_metrics(
    team_context: dict[str, dict[str, float]],
    team_name: str,
) -> dict[str, float]:
    defaults = team_context.get("_defaults", {})
    metrics = defaults.copy()
    metrics.update(team_context.get(team_name, {}))
    return metrics



