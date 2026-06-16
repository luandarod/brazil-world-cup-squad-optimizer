from pathlib import Path

import pandas as pd


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False)


def write_serving_outputs(
    base_dir: Path, leaderboard: pd.DataFrame, predictions: pd.DataFrame, teams: pd.DataFrame
) -> None:
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(output_dir / "model_leaderboard.csv", leaderboard)
    _write_csv(output_dir / "match_predictions.csv", predictions)
    _write_csv(output_dir / "team_summary.csv", teams)


def read_model_leaderboard(base_dir: Path) -> pd.DataFrame:
    return pd.read_csv(Path(base_dir) / "model_leaderboard.csv")


def read_match_predictions(base_dir: Path) -> pd.DataFrame:
    return pd.read_csv(Path(base_dir) / "match_predictions.csv")


def read_team_summary(base_dir: Path) -> pd.DataFrame:
    return pd.read_csv(Path(base_dir) / "team_summary.csv")
