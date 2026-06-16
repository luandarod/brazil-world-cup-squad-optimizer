from pathlib import Path
import sys
import uuid

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.serving.load_outputs import (
    read_match_predictions,
    read_model_leaderboard,
    read_team_summary,
    write_serving_outputs,
)


def _make_temp_dir() -> Path:
    temp_dir = Path(__file__).resolve().parents[1] / ".pytest_tmp" / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


def test_write_serving_outputs_creates_model_leaderboard_csv() -> None:
    temp_dir = _make_temp_dir()
    leaderboard = pd.DataFrame(
        [
            {
                "model_name": "baseline",
                "target_name": "goals",
                "mae": 0.45,
            }
        ]
    )
    predictions = pd.DataFrame(
        [
            {
                "match_id": "bra-vs-arg",
                "predicted_winner": "Brazil",
            }
        ]
    )
    teams = pd.DataFrame(
        [
            {
                "team": "Brazil",
                "squad_strength": 91.2,
            }
        ]
    )

    write_serving_outputs(temp_dir / "serving", leaderboard, predictions, teams)

    assert (temp_dir / "serving" / "model_leaderboard.csv").exists()
    assert (temp_dir / "serving" / "match_predictions.csv").exists()
    assert (temp_dir / "serving" / "team_summary.csv").exists()


def test_serving_output_readers_return_written_csv_contents() -> None:
    serving_dir = _make_temp_dir() / "serving"
    leaderboard = pd.DataFrame(
        [
            {
                "model_name": "shots-model",
                "target_name": "shots",
                "mae": 0.2,
            }
        ]
    )
    predictions = pd.DataFrame(
        [
            {
                "match_id": "bra-vs-uru",
                "predicted_winner": "Brazil",
            }
        ]
    )
    teams = pd.DataFrame(
        [
            {
                "team": "Uruguay",
                "squad_strength": 84.1,
            }
        ]
    )

    write_serving_outputs(serving_dir, leaderboard, predictions, teams)

    pd.testing.assert_frame_equal(read_model_leaderboard(serving_dir), leaderboard)
    pd.testing.assert_frame_equal(read_match_predictions(serving_dir), predictions)
    pd.testing.assert_frame_equal(read_team_summary(serving_dir), teams)
