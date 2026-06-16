from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.ingestion.espn_client import ESPNClient
from src.ingestion.fifa_client import FIFAClient
from src.serving.load_outputs import write_serving_outputs

OBSERVED_RESULT_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "home_shots",
    "away_shots",
    "status",
    "source",
    "source_retrieved_at",
]

LEADERBOARD_COLUMNS = ["model_name", "target_name", "mae"]
PREDICTION_COLUMNS = [
    "match_id",
    "predicted_home_goals",
    "predicted_away_goals",
    "predicted_winner",
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
    "goal_difference",
    "points",
]


def build_real_serving_snapshot(
    start_date: str,
    end_date: str,
    output_dir: Path,
    client: ESPNClient | None = None,
    disable_ssl_verification: bool = False,
) -> None:
    normalized_matches = _load_normalized_matches(
        start_date=start_date,
        end_date=end_date,
        client=client,
        disable_ssl_verification=disable_ssl_verification,
    )

    observed_results = pd.DataFrame(normalized_matches, columns=OBSERVED_RESULT_COLUMNS)
    coverage = _build_coverage_summary(observed_results)
    teams = _build_team_summary(observed_results)

    write_serving_outputs(
        output_dir,
        leaderboard=pd.DataFrame(columns=LEADERBOARD_COLUMNS),
        predictions=pd.DataFrame(columns=PREDICTION_COLUMNS),
        teams=teams,
        coverage_summary=coverage,
        observed_match_results=observed_results,
    )


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
                "status": "Final",
                "source": raw_match.get("source", "fifa"),
                "source_retrieved_at": raw_match.get("retrieved_at"),
            }
        )
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _build_coverage_summary(observed_results: pd.DataFrame) -> pd.DataFrame:
    total_matches = len(observed_results.index)
    shots_covered = 0
    if not observed_results.empty and {"home_shots", "away_shots"}.issubset(observed_results.columns):
        shots_covered = int(
            (
                observed_results["home_shots"].notna()
                & observed_results["away_shots"].notna()
            ).sum()
        )
    rows = []
    for metric_name, covered_matches in (
        ("goals", total_matches),
        ("cards", 0),
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
    parser.add_argument("--output-dir", default=str(Path("data/serving")))
    parser.add_argument("--disable-ssl-verification", action="store_true")
    args = parser.parse_args()

    build_real_serving_snapshot(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=Path(args.output_dir),
        disable_ssl_verification=args.disable_ssl_verification,
    )


if __name__ == "__main__":
    main()
