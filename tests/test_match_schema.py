from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.match_schema import PredictionRow, TeamMatchTruthRow


def test_team_match_truth_row_matches_team_match_contract() -> None:
    row = TeamMatchTruthRow(
        match_id="2026-07-15-bra-arg",
        match_date="2026-07-15",
        stage="group",
        team="Brazil",
        opponent="Argentina",
        is_home_team=False,
        goals_for=2,
        cards_for=3,
        shots_for=11,
        source="fifa",
    )

    assert row.model_dump() == {
        "match_id": "2026-07-15-bra-arg",
        "match_date": "2026-07-15",
        "stage": "group",
        "team": "Brazil",
        "opponent": "Argentina",
        "is_home_team": False,
        "goals_for": 2,
        "cards_for": 3,
        "shots_for": 11,
        "source": "fifa",
    }


def test_prediction_row_matches_prediction_contract() -> None:
    row = PredictionRow(
        match_id="2026-07-15-bra-arg",
        team="Brazil",
        model_name="poisson-regression",
        target_name="goals_for",
        predicted_value=1.8,
    )

    assert row.model_dump() == {
        "match_id": "2026-07-15-bra-arg",
        "team": "Brazil",
        "model_name": "poisson-regression",
        "target_name": "goals_for",
        "predicted_value": 1.8,
    }


def test_prediction_row_rejects_unrequested_fields() -> None:
    with pytest.raises(ValidationError):
        PredictionRow(
            match_id="2026-07-15-bra-arg",
            team="Brazil",
            model_name="poisson-regression",
            target_name="goals_for",
            predicted_value=1.8,
            win_probability=0.7,
        )
