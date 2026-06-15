from __future__ import annotations


def normalize_market_row(raw_row: dict) -> list[dict]:
    match_id = raw_row["match_id"]
    home_team = raw_row["home_team"]
    away_team = raw_row["away_team"]
    home_goal_line = raw_row["home_goal_line"]
    away_goal_line = raw_row["away_goal_line"]
    home_cards_line = raw_row["home_cards_line"]
    away_cards_line = raw_row["away_cards_line"]
    home_shots_line = raw_row["home_shots_line"]
    away_shots_line = raw_row["away_shots_line"]

    return [
        {
            "match_id": match_id,
            "team": home_team,
            "opponent": away_team,
            "expected_goals_market": home_goal_line,
            "expected_cards_market": home_cards_line,
            "expected_shots_market": home_shots_line,
        },
        {
            "match_id": match_id,
            "team": away_team,
            "opponent": home_team,
            "expected_goals_market": away_goal_line,
            "expected_cards_market": away_cards_line,
            "expected_shots_market": away_shots_line,
        },
    ]
