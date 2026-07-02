from pathlib import Path

import pandas as pd


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False)


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def write_serving_outputs(
    base_dir: Path,
    leaderboard: pd.DataFrame,
    predictions: pd.DataFrame,
    teams: pd.DataFrame,
    coverage_summary: pd.DataFrame | None = None,
    observed_match_results: pd.DataFrame | None = None,
    match_prediction_vs_actual: pd.DataFrame | None = None,
    group_forecast_summary: pd.DataFrame | None = None,
    knockout_forecast_summary: pd.DataFrame | None = None,
    team_forecast_summary: pd.DataFrame | None = None,
    methodology_status: pd.DataFrame | None = None,
    title_probability_summary: pd.DataFrame | None = None,
    top_scorer_forecast: pd.DataFrame | None = None,
    squad_optimizer_results: pd.DataFrame | None = None,
) -> None:
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(output_dir / "model_leaderboard.csv", leaderboard)
    _write_csv(output_dir / "match_predictions.csv", predictions)
    _write_csv(output_dir / "team_summary.csv", teams)
    optional_frames = {
        "coverage_summary.csv": coverage_summary,
        "observed_match_results.csv": observed_match_results,
        "match_prediction_vs_actual.csv": match_prediction_vs_actual,
        "group_forecast_summary.csv": group_forecast_summary,
        "knockout_forecast_summary.csv": knockout_forecast_summary,
        "team_forecast_summary.csv": team_forecast_summary,
        "methodology_status.csv": methodology_status,
        "title_probability_summary.csv": title_probability_summary,
        "top_scorer_forecast.csv": top_scorer_forecast,
        "squad_optimizer_results.csv": squad_optimizer_results,
    }
    for filename, frame in optional_frames.items():
        path = output_dir / filename
        if frame is not None:
            _write_csv(path, frame)
        else:
            _remove_if_exists(path)


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_model_leaderboard(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "model_leaderboard.csv")


def read_match_predictions(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "match_predictions.csv")


def read_team_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "team_summary.csv")


def read_coverage_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "coverage_summary.csv")


def read_observed_match_results(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "observed_match_results.csv")


def read_match_prediction_vs_actual(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "match_prediction_vs_actual.csv")


def read_group_forecast_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "group_forecast_summary.csv")


def read_knockout_forecast_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "knockout_forecast_summary.csv")


def read_team_forecast_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "team_forecast_summary.csv")


def read_methodology_status(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "methodology_status.csv")


def read_title_probability_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "title_probability_summary.csv")


def read_top_scorer_forecast(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "top_scorer_forecast.csv")


def read_squad_optimizer_results(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "squad_optimizer_results.csv")
