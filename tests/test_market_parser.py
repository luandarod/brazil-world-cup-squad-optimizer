from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.market_parser import normalize_market_row
from src.pipelines.build_market_dataset import build_market_dataset


def test_normalize_market_row_returns_two_team_rows_per_match() -> None:
    raw_row = {
        "match_id": "match-001",
        "match_date": "2026-06-15",
        "stage": "group",
        "home_team": "Brazil",
        "away_team": "Serbia",
        "home_win_odds": 1.8,
        "draw_odds": 3.4,
        "away_win_odds": 4.6,
    }

    assert normalize_market_row(raw_row) == [
        {
            "match_id": "match-001",
            "match_date": "2026-06-15",
            "stage": "group",
            "team": "Brazil",
            "opponent": "Serbia",
            "is_home_team": True,
            "team_win_odds": 1.8,
            "draw_odds": 3.4,
            "opponent_win_odds": 4.6,
            "source": "market",
        },
        {
            "match_id": "match-001",
            "match_date": "2026-06-15",
            "stage": "group",
            "team": "Serbia",
            "opponent": "Brazil",
            "is_home_team": False,
            "team_win_odds": 4.6,
            "draw_odds": 3.4,
            "opponent_win_odds": 1.8,
            "source": "market",
        },
    ]


def test_build_market_dataset_returns_sorted_rows() -> None:
    raw_rows = [
        {
            "match_id": "match-002",
            "match_date": "2026-06-16",
            "stage": "group",
            "home_team": "Japan",
            "away_team": "Brazil",
            "home_win_odds": 3.8,
            "draw_odds": 3.1,
            "away_win_odds": 1.9,
        },
        {
            "match_id": "match-001",
            "match_date": "2026-06-15",
            "stage": "group",
            "home_team": "Serbia",
            "away_team": "Argentina",
            "home_win_odds": 4.2,
            "draw_odds": 3.0,
            "away_win_odds": 1.7,
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
        "match_date",
        "stage",
        "team",
        "opponent",
        "is_home_team",
        "team_win_odds",
        "draw_odds",
        "opponent_win_odds",
        "source",
    ]
    assert dataset.empty
    expected = pd.DataFrame(columns=dataset.columns)
    pd.testing.assert_frame_equal(dataset, expected)
