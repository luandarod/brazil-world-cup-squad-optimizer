from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.fifa_parser import parse_team_match_rows
from src.pipelines.build_truth_dataset import build_truth_dataset


def test_parse_team_match_rows_returns_two_team_rows_per_match() -> None:
    raw_match = {
        "id": "match-001",
        "date": "2026-06-15",
        "stage": "group",
        "home_team": {
            "name": "Brazil",
            "goals": 2,
            "cards": 1,
            "shots": 8,
        },
        "away_team": {
            "name": "Serbia",
            "goals": 1,
            "cards": 3,
            "shots": 5,
        },
    }

    assert parse_team_match_rows(raw_match) == [
        {
            "match_id": "match-001",
            "match_date": "2026-06-15",
            "stage": "group",
            "team": "Brazil",
            "opponent": "Serbia",
            "is_home_team": True,
            "goals_for": 2,
            "cards_for": 1,
            "shots_for": 8,
            "source": "fifa",
        },
        {
            "match_id": "match-001",
            "match_date": "2026-06-15",
            "stage": "group",
            "team": "Serbia",
            "opponent": "Brazil",
            "is_home_team": False,
            "goals_for": 1,
            "cards_for": 3,
            "shots_for": 5,
            "source": "fifa",
        },
    ]


def test_build_truth_dataset_returns_sorted_rows() -> None:
    raw_matches = [
        {
            "id": "match-002",
            "date": "2026-06-16",
            "stage": "group",
            "home_team": {"name": "Japan", "goals": 1, "cards": 2, "shots": 4},
            "away_team": {"name": "Brazil", "goals": 2, "cards": 1, "shots": 9},
        },
        {
            "id": "match-001",
            "date": "2026-06-15",
            "stage": "group",
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


def test_build_truth_dataset_returns_empty_dataframe_with_stable_columns() -> None:
    dataset = build_truth_dataset([])

    assert list(dataset.columns) == [
        "match_id",
        "match_date",
        "stage",
        "team",
        "opponent",
        "is_home_team",
        "goals_for",
        "cards_for",
        "shots_for",
        "source",
    ]
    assert dataset.empty
    assert_frame = pd.DataFrame(columns=dataset.columns)
    pd.testing.assert_frame_equal(dataset, assert_frame)
