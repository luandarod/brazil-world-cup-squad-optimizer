from __future__ import annotations


def normalize_market_row(raw_row: dict) -> list[dict]:
    match_id = raw_row["match_id"]
    match_date = raw_row["match_date"]
    stage = raw_row["stage"]
    home_team = raw_row["home_team"]
    away_team = raw_row["away_team"]
    home_win_odds = raw_row["home_win_odds"]
    draw_odds = raw_row["draw_odds"]
    away_win_odds = raw_row["away_win_odds"]

    return [
        {
            "match_id": match_id,
            "match_date": match_date,
            "stage": stage,
            "team": home_team,
            "opponent": away_team,
            "is_home_team": True,
            "team_win_odds": home_win_odds,
            "draw_odds": draw_odds,
            "opponent_win_odds": away_win_odds,
            "source": "market",
        },
        {
            "match_id": match_id,
            "match_date": match_date,
            "stage": stage,
            "team": away_team,
            "opponent": home_team,
            "is_home_team": False,
            "team_win_odds": away_win_odds,
            "draw_odds": draw_odds,
            "opponent_win_odds": home_win_odds,
            "source": "market",
        },
    ]
