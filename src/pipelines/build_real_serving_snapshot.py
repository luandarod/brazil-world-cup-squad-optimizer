from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.ingestion.espn_client import ESPNClient
from src.serving.load_outputs import write_serving_outputs

OBSERVED_RESULT_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
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
    fetch_client = client or ESPNClient(verify_ssl=not disable_ssl_verification)
    normalized_matches = _fetch_completed_matches(fetch_client, start_date, end_date)

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


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _build_coverage_summary(observed_results: pd.DataFrame) -> pd.DataFrame:
    total_matches = len(observed_results.index)
    rows = []
    for metric_name, covered_matches in (
        ("goals", total_matches),
        ("cards", 0),
        ("shots", 0),
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
