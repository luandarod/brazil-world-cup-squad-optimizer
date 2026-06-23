from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.match_schema import PredictionRow, PublicMatchTruthRow, TeamMatchTruthRow
from src.ingestion.lineup_client import LineupClient


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
        "fouls_for": 0,
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


def test_team_match_truth_row_rejects_invalid_match_date() -> None:
    with pytest.raises(ValidationError):
        TeamMatchTruthRow(
            match_id="2026-07-15-bra-arg",
            match_date="2026-15-99",
            stage="group",
            team="Brazil",
            opponent="Argentina",
            is_home_team=False,
            goals_for=2,
            cards_for=3,
            shots_for=11,
            source="fifa",
        )


@pytest.mark.parametrize("field_name", ["goals_for", "cards_for", "shots_for"])
def test_team_match_truth_row_rejects_negative_match_stats(field_name: str) -> None:
    payload = {
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
    payload[field_name] = -1

    with pytest.raises(ValidationError):
        TeamMatchTruthRow(**payload)


@pytest.mark.parametrize("predicted_value", [float("nan"), float("inf"), float("-inf"), -0.1])
def test_prediction_row_rejects_non_finite_or_negative_values(predicted_value: float) -> None:
    with pytest.raises(ValidationError):
        PredictionRow(
            match_id="2026-07-15-bra-arg",
            team="Brazil",
            model_name="poisson-regression",
            target_name="goals_for",
            predicted_value=predicted_value,
        )


def test_public_match_truth_row_supports_player_context_fields() -> None:
    row = PublicMatchTruthRow(
        match_id="760419",
        match_date="2026-06-13",
        stage="Group C",
        home_team="Brazil",
        away_team="Morocco",
        home_goals=1,
        away_goals=1,
        home_shots=12,
        away_shots=14,
        home_cards=None,
        away_cards=None,
        home_fouls=12,
        away_fouls=15,
        status="Full Time",
        source="espn",
        source_retrieved_at="2026-06-19T12:00:00Z",
        is_future_fixture=False,
        home_lineup_confirmed=True,
        away_lineup_confirmed=True,
        home_probable_lineup_count=11,
        away_probable_lineup_count=11,
        home_substitutions_used=5,
        away_substitutions_used=4,
    )

    assert row.model_dump()["home_substitutions_used"] == 5
    assert row.model_dump()["source_retrieved_at"] == "2026-06-19T12:00:00Z"
    assert row.model_dump()["home_fouls"] == 12


def test_lineup_client_returns_default_player_context_contract() -> None:
    assert LineupClient().fetch_match_player_context("760419") == {
        "home_lineup_confirmed": False,
        "away_lineup_confirmed": False,
        "home_probable_lineup_count": 0,
        "away_probable_lineup_count": 0,
        "home_substitutions_used": 0,
        "away_substitutions_used": 0,
    }
