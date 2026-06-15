from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.fifa_client import FIFAClient
from src.ingestion.fifa_parser import parse_team_match_rows


def build_truth_dataset(raw_matches: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for raw_match in raw_matches:
        rows.extend(parse_team_match_rows(raw_match))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    output_path = Path("data/processed/world_cup_2026_truth_team_match.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = FIFAClient()
    dataset = build_truth_dataset(client.fetch_world_cup_matches())
    dataset.to_csv(output_path, index=False)
