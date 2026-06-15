from __future__ import annotations


def parse_team_match_rows(raw_match: dict) -> list[dict]:
    match_id = raw_match["id"]
    match_date = raw_match["date"]
    stage = raw_match["stage"]
    home_team = raw_match["home_team"]
    away_team = raw_match["away_team"]

    return [
        {
            "match_id": match_id,
            "match_date": match_date,
            "stage": stage,
            "team": home_team["name"],
            "opponent": away_team["name"],
            "is_home_team": True,
            "goals_for": home_team["goals"],
            "cards_for": home_team["cards"],
            "shots_for": home_team["shots"],
            "source": "fifa",
        },
        {
            "match_id": match_id,
            "match_date": match_date,
            "stage": stage,
            "team": away_team["name"],
            "opponent": home_team["name"],
            "is_home_team": False,
            "goals_for": away_team["goals"],
            "cards_for": away_team["cards"],
            "shots_for": away_team["shots"],
            "source": "fifa",
        },
    ]
