"""Baseline model placeholders for future forecasting work."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineModelSpec:
    model_name: str = "baseline"
    description: str = "Placeholder baseline contract for evaluation wiring."
