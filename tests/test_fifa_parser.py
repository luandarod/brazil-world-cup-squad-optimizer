from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.fifa_client import _normalize_match
from src.ingestion.fifa_parser import parse_team_match_rows
from src.pipelines.build_truth_dataset import build_truth_dataset


def test_parse_team_match_rows_marks_partial_metric_coverage() -> None:
    raw_match = {
        "id": "match-003",
        "date": "2026-06-17",
        "stage": "group",
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": None,
        "shooting_source": None,
        "retrieved_at": "2026-06-16T22:00:00Z",
        "home_team": {
            "name": "Brazil",
            "goals": 3,
            "cards": None,
            "shots": None,
        },
        "away_team": {
            "name": "Mexico",
            "goals": 1,
            "cards": None,
            "shots": None,
        },
    }

    assert parse_team_match_rows(raw_match)[0] == {
        "match_id": "match-003",
        "match_date": "2026-06-17",
        "stage": "group",
        "team": "Brazil",
        "opponent": "Mexico",
        "is_home_team": True,
        "is_observed_match": True,
        "goals_for": 3,
        "cards_for": None,
        "shots_for": None,
        "has_goals_truth": True,
        "has_cards_truth": False,
        "has_shots_truth": False,
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": None,
        "shooting_source": None,
        "source_retrieved_at": "2026-06-16T22:00:00Z",
    }


def test_build_truth_dataset_returns_sorted_rows() -> None:
    raw_matches = [
        {
            "id": "match-002",
            "date": "2026-06-16",
            "stage": "group",
            "source": "fifa",
            "score_source": "fifa",
            "discipline_source": "fifa",
            "shooting_source": None,
            "retrieved_at": "2026-06-16T20:00:00Z",
            "home_team": {"name": "Japan", "goals": 1, "cards": 2, "shots": 4},
            "away_team": {"name": "Brazil", "goals": 2, "cards": 1, "shots": 9},
        },
        {
            "id": "match-001",
            "date": "2026-06-15",
            "stage": "group",
            "source": "fifa",
            "score_source": "fifa",
            "discipline_source": None,
            "shooting_source": None,
            "retrieved_at": "2026-06-16T19:00:00Z",
            "home_team": {"name": "Serbia", "goals": 0, "cards": 3, "shots": 5},
            "away_team": {"name": "Argentina", "goals": 1, "cards": 2, "shots": 7},
        },
    ]

    dataset = build_truth_dataset(raw_matches)

    assert dataset[["match_date", "match_id", "team"]].to_dict("records") == [
        {"match_date": "2026-06-15", "match_id": "match-001", "team": "Argentina"},
        {"match_date": "2026-06-15", "match_id": "match-001", "team": "Serbia"},
        {"match_date": "2026-06-16", "match_id": "match-002", "team": "Brazil"},
        {"match_date": "2026-06-16", "match_id": "match-002", "team": "Japan"},
    ]


def test_build_truth_dataset_returns_empty_dataframe_with_coverage_columns() -> None:
    dataset = build_truth_dataset([])

    assert list(dataset.columns) == [
        "match_id",
        "match_date",
        "stage",
        "team",
        "opponent",
        "is_home_team",
        "is_observed_match",
        "goals_for",
        "cards_for",
        "shots_for",
        "has_goals_truth",
        "has_cards_truth",
        "has_shots_truth",
        "source",
        "score_source",
        "discipline_source",
        "shooting_source",
        "source_retrieved_at",
    ]
    assert dataset.empty
    assert_frame = pd.DataFrame(columns=dataset.columns)
    pd.testing.assert_frame_equal(dataset, assert_frame)


def test_normalize_match_skips_unplayed_matches() -> None:
    candidate = {
        "id": "match-upcoming",
        "date": "2026-06-20T18:00:00Z",
        "stage": "group",
        "status": "scheduled",
        "homeTeam": {"name": "Brazil", "score": None},
        "awayTeam": {"name": "Mexico", "score": None},
    }

    assert _normalize_match(candidate, retrieved_at="2026-06-16T22:00:00Z") is None


def test_normalize_match_sets_metric_sources_only_when_fifa_payload_has_them() -> None:
    candidate = {
        "id": "match-finished",
        "date": "2026-06-20T18:00:00Z",
        "stage": "group",
        "status": "completed",
        "homeTeam": {
            "name": "Brazil",
            "score": 2,
            "yellowCards": 1,
            "shotsTotal": 8,
        },
        "awayTeam": {
            "name": "Mexico",
            "score": 1,
            "yellowCards": 3,
            "shotsTotal": 5,
        },
    }

    assert _normalize_match(candidate, retrieved_at="2026-06-16T22:00:00Z") == {
        "id": "match-finished",
        "date": "2026-06-20",
        "stage": "group",
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": "fifa",
        "shooting_source": "fifa",
        "retrieved_at": "2026-06-16T22:00:00Z",
        "home_team": {"name": "Brazil", "goals": 2, "cards": 1, "shots": 8},
        "away_team": {"name": "Mexico", "goals": 1, "cards": 3, "shots": 5},
    }


def test_normalize_match_skips_no_status_zero_zero_placeholder_fixture() -> None:
    candidate = {
        "id": "match-placeholder",
        "date": "2026-06-21T18:00:00Z",
        "stage": "group",
        "homeTeam": {"name": "Brazil", "score": 0},
        "awayTeam": {"name": "Mexico", "score": "0"},
    }

    assert _normalize_match(candidate, retrieved_at="2026-06-16T22:00:00Z") is None


def test_parse_team_match_rows_sets_metric_sources_per_team_row() -> None:
    raw_match = {
        "id": "match-004",
        "date": "2026-06-18",
        "stage": "group",
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": "fifa",
        "shooting_source": "fifa",
        "retrieved_at": "2026-06-16T22:30:00Z",
        "home_team": {
            "name": "Brazil",
            "goals": 2,
            "cards": 1,
            "shots": 6,
        },
        "away_team": {
            "name": "Mexico",
            "goals": 1,
            "cards": None,
            "shots": None,
        },
    }

    rows = parse_team_match_rows(raw_match)

    assert rows[0]["discipline_source"] == "fifa"
    assert rows[0]["shooting_source"] == "fifa"
    assert rows[1]["discipline_source"] is None
    assert rows[1]["shooting_source"] is None
