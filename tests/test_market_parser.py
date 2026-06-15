from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.market_parser import normalize_market_row
from src.pipelines.build_market_dataset import build_market_dataset


def test_normalize_market_row_returns_two_team_rows_per_match() -> None:
    raw_row = {
        "match_id": "match-001",
        "home_team": "Brazil",
        "away_team": "Serbia",
        "home_goal_line": 2.1,
        "away_goal_line": 0.8,
        "home_cards_line": 1.7,
        "away_cards_line": 2.9,
        "home_shots_line": 8.4,
        "away_shots_line": 4.6,
    }

    assert normalize_market_row(raw_row) == [
        {
            "match_id": "match-001",
            "team": "Brazil",
            "opponent": "Serbia",
            "expected_goals_market": 2.1,
            "expected_cards_market": 1.7,
            "expected_shots_market": 8.4,
        },
        {
            "match_id": "match-001",
            "team": "Serbia",
            "opponent": "Brazil",
            "expected_goals_market": 0.8,
            "expected_cards_market": 2.9,
            "expected_shots_market": 4.6,
        },
    ]


def test_build_market_dataset_returns_sorted_rows() -> None:
    raw_rows = [
        {
            "match_id": "match-002",
            "home_team": "Japan",
            "away_team": "Brazil",
            "home_goal_line": 1.0,
            "away_goal_line": 2.2,
            "home_cards_line": 2.5,
            "away_cards_line": 1.1,
            "home_shots_line": 5.7,
            "away_shots_line": 9.4,
        },
        {
            "match_id": "match-001",
            "home_team": "Serbia",
            "away_team": "Argentina",
            "home_goal_line": 0.9,
            "away_goal_line": 1.8,
            "home_cards_line": 3.0,
            "away_cards_line": 2.0,
            "home_shots_line": 4.8,
            "away_shots_line": 7.1,
        },
    ]

    dataset = build_market_dataset(raw_rows)

    assert dataset[["match_id", "team"]].to_dict("records") == [
        {"match_id": "match-001", "team": "Argentina"},
        {"match_id": "match-001", "team": "Serbia"},
        {"match_id": "match-002", "team": "Brazil"},
        {"match_id": "match-002", "team": "Japan"},
    ]


def test_build_market_dataset_returns_empty_dataframe_with_stable_columns() -> None:
    dataset = build_market_dataset([])

    assert list(dataset.columns) == [
        "match_id",
        "team",
        "opponent",
        "expected_goals_market",
        "expected_cards_market",
        "expected_shots_market",
    ]
    assert dataset.empty
    expected = pd.DataFrame(columns=dataset.columns)
    pd.testing.assert_frame_equal(dataset, expected)
