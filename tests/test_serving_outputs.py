from pathlib import Path
import sys
import tempfile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.serving.load_outputs import (
    read_coverage_summary,
    read_match_predictions,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_summary,
    write_serving_outputs,
)
def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="serving-outputs-"))


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
    pd.testing.assert_frame_equal(read_coverage_summary(temp_dir / "serving"), pd.DataFrame())
    pd.testing.assert_frame_equal(read_observed_match_results(temp_dir / "serving"), pd.DataFrame())


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
    coverage = pd.DataFrame(
        [
            {
                "target_name": "goals",
                "coverage": 0.88,
            }
        ]
    )
    observed_results = pd.DataFrame(
        [
            {
                "match_id": "bra-vs-uru",
                "winner": "Brazil",
            }
        ]
    )

    write_serving_outputs(
        serving_dir,
        leaderboard,
        predictions,
        teams,
        coverage,
        observed_results,
    )

    pd.testing.assert_frame_equal(read_model_leaderboard(serving_dir), leaderboard)
    pd.testing.assert_frame_equal(read_match_predictions(serving_dir), predictions)
    pd.testing.assert_frame_equal(read_team_summary(serving_dir), teams)
    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), coverage)
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), observed_results)


def test_write_serving_outputs_writes_new_artifacts_when_provided() -> None:
    serving_dir = _make_temp_dir() / "serving"
    leaderboard = pd.DataFrame([{"model_name": "xgboost", "target_name": "winner", "mae": 0.11}])
    predictions = pd.DataFrame([{"match_id": "bra-vs-fra", "predicted_winner": "Brazil"}])
    teams = pd.DataFrame([{"team": "France", "squad_strength": 89.3}])
    coverage = pd.DataFrame([{"target_name": "winner", "coverage": 0.96}])
    observed_results = pd.DataFrame([{"match_id": "bra-vs-fra", "winner": "Brazil"}])

    write_serving_outputs(
        serving_dir,
        leaderboard,
        predictions,
        teams,
        coverage,
        observed_results,
    )

    assert (serving_dir / "coverage_summary.csv").exists()
    assert (serving_dir / "observed_match_results.csv").exists()
    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), coverage)
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), observed_results)


def test_old_writer_call_clears_stale_optional_artifacts_in_reused_directory() -> None:
    serving_dir = _make_temp_dir() / "serving"
    leaderboard = pd.DataFrame([{"model_name": "elo", "target_name": "winner", "mae": 0.19}])
    predictions = pd.DataFrame([{"match_id": "bra-vs-ger", "predicted_winner": "Brazil"}])
    teams = pd.DataFrame([{"team": "Germany", "squad_strength": 86.5}])
    coverage = pd.DataFrame([{"target_name": "winner", "coverage": 0.91}])
    observed_results = pd.DataFrame([{"match_id": "bra-vs-ger", "winner": "Brazil"}])

    write_serving_outputs(
        serving_dir,
        leaderboard,
        predictions,
        teams,
        coverage,
        observed_results,
    )

    write_serving_outputs(serving_dir, leaderboard, predictions, teams)

    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), pd.DataFrame())


def test_new_serving_output_readers_return_empty_frames_when_files_are_missing() -> None:
    serving_dir = _make_temp_dir() / "serving"

    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), pd.DataFrame())
