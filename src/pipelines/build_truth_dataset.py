from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.fifa_client import FIFAClient
from src.ingestion.fifa_parser import parse_team_match_rows

TRUTH_DATASET_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "team",
    "opponent",
    "is_home_team",
    "is_observed_match",
    "goals_for",
    "cards_for",
    "shots_for",
    "has_goals_truth",
    "has_cards_truth",
    "has_shots_truth",
    "source",
    "score_source",
    "discipline_source",
    "shooting_source",
    "source_retrieved_at",
]


def build_truth_dataset(raw_matches: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for raw_match in raw_matches:
        rows.extend(parse_team_match_rows(raw_match))

    dataset = pd.DataFrame(rows, columns=TRUTH_DATASET_COLUMNS)
    if dataset.empty:
        return dataset

    return dataset.sort_values(["match_date", "match_id", "team"]).reset_index(drop=True)


if __name__ == "__main__":
    output_path = Path("data/processed/world_cup_2026_truth_team_match.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = FIFAClient()
    dataset = build_truth_dataset(client.fetch_world_cup_matches())
    dataset.to_csv(output_path, index=False)
