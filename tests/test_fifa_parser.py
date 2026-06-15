from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.fifa_parser import parse_team_match_rows


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
