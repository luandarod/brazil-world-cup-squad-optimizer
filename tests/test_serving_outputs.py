from pathlib import Path
import sys
import tempfile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.serving.load_outputs import (
    read_coverage_summary,
    read_group_forecast_summary,
    read_knockout_forecast_summary,
    read_match_predictions,
    read_match_prediction_vs_actual,
    read_methodology_status,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_forecast_summary,
    read_team_summary,
    read_title_probability_summary,
    read_top_scorer_forecast,
    read_squad_optimizer_results,
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
    comparisons = pd.DataFrame([{"match_id": "bra-vs-fra", "winner_hit": 1.0}])
    groups = pd.DataFrame([{"group_stage": "Group A", "team": "Brazil", "projected_total_points": 7.0}])
    knockout = pd.DataFrame([{"stage": "Quarterfinal", "match_id": "qf-1", "predicted_winner": "Brazil"}])
    team_forecasts = pd.DataFrame([{"team": "France", "projected_points": 1.0}])
    methodology = pd.DataFrame([{"metric_name": "goals", "publish_status": "published"}])
    title_probability = pd.DataFrame([{"team": "Brazil", "title_probability_pct": 12.4}])
    top_scorers = pd.DataFrame([{"player_name": "A", "projected_total_goals": 4.2}])
    squad_optimizer = pd.DataFrame([{"player_name": "Alisson", "score_final": 95.0}])
 
    write_serving_outputs(
        serving_dir,
        leaderboard,
        predictions,
        teams,
        coverage,
        observed_results,
        comparisons,
        groups,
        knockout,
        team_forecasts,
        methodology,
        title_probability,
        top_scorers,
        squad_optimizer,
    )
 
    assert (serving_dir / "coverage_summary.csv").exists()
    assert (serving_dir / "observed_match_results.csv").exists()
    assert (serving_dir / "match_prediction_vs_actual.csv").exists()
    assert (serving_dir / "group_forecast_summary.csv").exists()
    assert (serving_dir / "knockout_forecast_summary.csv").exists()
    assert (serving_dir / "team_forecast_summary.csv").exists()
    assert (serving_dir / "methodology_status.csv").exists()
    assert (serving_dir / "title_probability_summary.csv").exists()
    assert (serving_dir / "top_scorer_forecast.csv").exists()
    assert (serving_dir / "squad_optimizer_results.csv").exists()
    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), coverage)
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), observed_results)
    pd.testing.assert_frame_equal(read_match_prediction_vs_actual(serving_dir), comparisons)
    pd.testing.assert_frame_equal(read_group_forecast_summary(serving_dir), groups)
    pd.testing.assert_frame_equal(read_knockout_forecast_summary(serving_dir), knockout)
    pd.testing.assert_frame_equal(read_team_forecast_summary(serving_dir), team_forecasts)
    pd.testing.assert_frame_equal(read_methodology_status(serving_dir), methodology)
    pd.testing.assert_frame_equal(read_title_probability_summary(serving_dir), title_probability)
    pd.testing.assert_frame_equal(read_top_scorer_forecast(serving_dir), top_scorers)
    pd.testing.assert_frame_equal(read_squad_optimizer_results(serving_dir), squad_optimizer)


def test_old_writer_call_clears_stale_optional_artifacts_in_reused_directory() -> None:
    serving_dir = _make_temp_dir() / "serving"
    leaderboard = pd.DataFrame([{"model_name": "elo", "target_name": "winner", "mae": 0.19}])
    predictions = pd.DataFrame([{"match_id": "bra-vs-ger", "predicted_winner": "Brazil"}])
    teams = pd.DataFrame([{"team": "Germany", "squad_strength": 86.5}])
    coverage = pd.DataFrame([{"target_name": "winner", "coverage": 0.91}])
    observed_results = pd.DataFrame([{"match_id": "bra-vs-ger", "winner": "Brazil"}])
    comparisons = pd.DataFrame([{"match_id": "bra-vs-ger", "winner_hit": 1.0}])
    groups = pd.DataFrame([{"group_stage": "Group A", "team": "Brazil", "projected_total_points": 7.0}])
    knockout = pd.DataFrame([{"stage": "Quarterfinal", "match_id": "qf-1", "predicted_winner": "Brazil"}])
    team_forecasts = pd.DataFrame([{"team": "Germany", "projected_points": 0.0}])
    methodology = pd.DataFrame([{"metric_name": "goals", "publish_status": "published"}])
    title_probability = pd.DataFrame([{"team": "Brazil", "title_probability_pct": 12.4}])
    top_scorers = pd.DataFrame([{"player_name": "A", "projected_total_goals": 4.2}])

    write_serving_outputs(
        serving_dir,
        leaderboard,
        predictions,
        teams,
        coverage,
        observed_results,
        comparisons,
        groups,
        knockout,
        team_forecasts,
        methodology,
        title_probability,
        top_scorers,
    )

    write_serving_outputs(serving_dir, leaderboard, predictions, teams)

    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_match_prediction_vs_actual(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_group_forecast_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_knockout_forecast_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_team_forecast_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_methodology_status(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_title_probability_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_top_scorer_forecast(serving_dir), pd.DataFrame())


def test_new_serving_output_readers_return_empty_frames_when_files_are_missing() -> None:
    serving_dir = _make_temp_dir() / "serving"

    pd.testing.assert_frame_equal(read_coverage_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_observed_match_results(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_match_prediction_vs_actual(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_group_forecast_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_knockout_forecast_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_team_forecast_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_methodology_status(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_title_probability_summary(serving_dir), pd.DataFrame())
    pd.testing.assert_frame_equal(read_top_scorer_forecast(serving_dir), pd.DataFrame())
