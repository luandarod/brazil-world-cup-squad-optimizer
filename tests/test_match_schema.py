from datetime import date
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.match_schema import PredictionRow, TeamMatchTruthRow


def test_team_match_truth_row_parses_match_results() -> None:
    row = TeamMatchTruthRow(
        match_id="2026-07-15-bra-arg",
        team="Brazil",
        opponent="Argentina",
        match_date="2026-07-15",
        goals_for=2,
        goals_against=1,
    )

    assert row.match_id == "2026-07-15-bra-arg"
    assert row.match_date == date(2026, 7, 15)
    assert row.goals_for == 2
    assert row.goals_against == 1


def test_prediction_row_rejects_probability_above_one() -> None:
    with pytest.raises(ValidationError):
        PredictionRow(
            match_id="2026-07-15-bra-arg",
            team="Brazil",
            opponent="Argentina",
            match_date="2026-07-15",
            predicted_goals_for=1.8,
            predicted_goals_against=0.9,
            win_probability=1.2,
        )
