from __future__ import annotations


def parse_team_match_rows(raw_match: dict) -> list[dict]:
    return [
        _build_team_row(raw_match, "home_team", "away_team", True),
        _build_team_row(raw_match, "away_team", "home_team", False),
    ]


def _build_team_row(
    raw_match: dict,
    team_key: str,
    opponent_key: str,
    is_home_team: bool,
) -> dict:
    team = raw_match[team_key]
    return {
        "match_id": raw_match["id"],
        "match_date": raw_match["date"],
        "stage": raw_match["stage"],
        "team": team["name"],
        "opponent": raw_match[opponent_key]["name"],
        "is_home_team": is_home_team,
        "is_observed_match": True,
        "goals_for": team.get("goals"),
        "cards_for": team.get("cards"),
        "shots_for": team.get("shots"),
        "has_goals_truth": team.get("goals") is not None,
        "has_cards_truth": team.get("cards") is not None,
        "has_shots_truth": team.get("shots") is not None,
        "source": raw_match.get("source", "fifa"),
        "score_source": raw_match.get("score_source"),
        "discipline_source": raw_match.get("discipline_source"),
        "shooting_source": raw_match.get("shooting_source"),
        "source_retrieved_at": raw_match.get("retrieved_at"),
    }
