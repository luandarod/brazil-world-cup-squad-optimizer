from __future__ import annotations


class LineupClient:
    def fetch_match_player_context(self, match_id: str) -> dict:
        return {
            "home_lineup_confirmed": False,
            "away_lineup_confirmed": False,
            "home_probable_lineup_count": 0,
            "away_probable_lineup_count": 0,
            "home_substitutions_used": 0,
            "away_substitutions_used": 0,
        }
