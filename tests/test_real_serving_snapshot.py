from pathlib import Path
import sys
import tempfile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipelines.build_real_serving_snapshot import build_real_serving_snapshot
from src.serving.load_outputs import (
    read_coverage_summary,
    read_match_predictions,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_summary,
)


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="real-serving-snapshot-"))


def test_build_real_serving_snapshot_writes_honest_outputs() -> None:
    class StubClient:
        def fetch_completed_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-11":
                return [
                    {
                        "match_id": "401",
                        "match_date": "2026-06-11",
                        "stage": "GROUP",
                        "home_team": "Brazil",
                        "away_team": "Mexico",
                        "home_goals": 3,
                        "away_goals": 1,
                        "status": "Final",
                        "source": "espn",
                        "source_retrieved_at": "2026-06-16T12:00:00Z",
                    }
                ]
            if str(match_date) == "2026-06-12":
                return [
                    {
                        "match_id": "402",
                        "match_date": "2026-06-12",
                        "stage": "GROUP",
                        "home_team": "France",
                        "away_team": "Brazil",
                        "home_goals": 0,
                        "away_goals": 0,
                        "status": "Final",
                        "source": "espn",
                        "source_retrieved_at": "2026-06-16T12:00:00Z",
                    }
                ]
            return []

    serving_dir = _make_temp_dir() / "serving"
    build_real_serving_snapshot(
        start_date="2026-06-11",
        end_date="2026-06-12",
        output_dir=serving_dir,
        client=StubClient(),
    )

    observed = read_observed_match_results(serving_dir)
    assert list(observed.columns) == [
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
    assert observed.to_dict("records") == [
        {
            "match_id": 401,
            "match_date": "2026-06-11",
            "stage": "GROUP",
            "home_team": "Brazil",
            "away_team": "Mexico",
            "home_goals": 3,
            "away_goals": 1,
            "status": "Final",
            "source": "espn",
            "source_retrieved_at": "2026-06-16T12:00:00Z",
        },
        {
            "match_id": 402,
            "match_date": "2026-06-12",
            "stage": "GROUP",
            "home_team": "France",
            "away_team": "Brazil",
            "home_goals": 0,
            "away_goals": 0,
            "status": "Final",
            "source": "espn",
            "source_retrieved_at": "2026-06-16T12:00:00Z",
        },
    ]

    coverage = read_coverage_summary(serving_dir)
    assert coverage.to_dict("records") == [
        {
            "metric_name": "goals",
            "covered_matches": 2,
            "total_matches": 2,
            "coverage_pct": 100.0,
            "has_truth": True,
        },
        {
            "metric_name": "cards",
            "covered_matches": 0,
            "total_matches": 2,
            "coverage_pct": 0.0,
            "has_truth": False,
        },
        {
            "metric_name": "shots",
            "covered_matches": 0,
            "total_matches": 2,
            "coverage_pct": 0.0,
            "has_truth": False,
        },
    ]

    teams = read_team_summary(serving_dir)
    assert teams.to_dict("records") == [
        {
            "team": "Brazil",
            "matches_played": 2,
            "wins": 1,
            "draws": 1,
            "losses": 0,
            "goals_for": 3,
            "goals_against": 1,
            "goal_difference": 2,
            "points": 4,
        },
        {
            "team": "France",
            "matches_played": 1,
            "wins": 0,
            "draws": 1,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 1,
        },
        {
            "team": "Mexico",
            "matches_played": 1,
            "wins": 0,
            "draws": 0,
            "losses": 1,
            "goals_for": 1,
            "goals_against": 3,
            "goal_difference": -2,
            "points": 0,
        },
    ]

    assert list(read_model_leaderboard(serving_dir).columns) == ["model_name", "target_name", "mae"]
    assert read_model_leaderboard(serving_dir).empty
    assert list(read_match_predictions(serving_dir).columns) == [
        "match_id",
        "predicted_home_goals",
        "predicted_away_goals",
        "predicted_winner",
    ]
    assert read_match_predictions(serving_dir).empty
