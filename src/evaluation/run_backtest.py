"""Backtest execution entrypoint."""

import pandas as pd

from src.evaluation.metrics import score_predictions


def run_backtest(predictions: pd.DataFrame) -> pd.DataFrame:
    """Run the current backtest evaluation over a predictions table."""
    return score_predictions(predictions)
