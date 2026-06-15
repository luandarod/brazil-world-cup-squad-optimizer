from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.market_client import MarketClient
from src.ingestion.market_parser import normalize_market_row

MARKET_DATASET_COLUMNS = [
    "match_id",
    "team",
    "opponent",
    "expected_goals_market",
    "expected_cards_market",
    "expected_shots_market",
]


def build_market_dataset(raw_rows: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for raw_row in raw_rows:
        rows.extend(normalize_market_row(raw_row))

    dataset = pd.DataFrame(rows, columns=MARKET_DATASET_COLUMNS)
    if dataset.empty:
        return dataset

    return dataset.sort_values(["match_id", "team"]).reset_index(drop=True)


if __name__ == "__main__":
    output_path = Path("data/processed/world_cup_2026_market_team_match.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = MarketClient()
    dataset = build_market_dataset(client.fetch_world_cup_market_rows())
    dataset.to_csv(output_path, index=False)
