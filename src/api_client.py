import requests
import pandas as pd
from .config import API_FOOTBALL_KEY, API_FOOTBALL_HOST

BASE_URL = f"https://{API_FOOTBALL_HOST}"

class APIFootballClient:
    """
    Cliente simples para API-Football.
    Documentação: https://www.api-football.com/documentation-v3
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or API_FOOTBALL_KEY
        if not self.api_key:
            raise ValueError("API_FOOTBALL_KEY não encontrada. Configure o arquivo .env.")

        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": API_FOOTBALL_HOST,
        }

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        response = requests.get(url, headers=self.headers, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def search_player(self, player_name: str, season: int = 2025) -> pd.DataFrame:
        payload = self.get("/players", {"search": player_name, "season": season})
        rows = []

        for item in payload.get("response", []):
            player = item.get("player", {})
            for stat in item.get("statistics", []):
                team = stat.get("team", {})
                league = stat.get("league", {})
                games = stat.get("games", {})
                goals = stat.get("goals", {})
                passes = stat.get("passes", {})
                cards = stat.get("cards", {})
                duels = stat.get("duels", {})
                tackles = stat.get("tackles", {})

                rows.append({
                    "player_id": player.get("id"),
                    "player_name": player.get("name"),
                    "age": player.get("age"),
                    "nationality": player.get("nationality"),
                    "team": team.get("name"),
                    "league": league.get("name"),
                    "country": league.get("country"),
                    "season": league.get("season"),
                    "position": games.get("position"),
                    "appearances": games.get("appearences"),
                    "lineups": games.get("lineups"),
                    "minutes": games.get("minutes"),
                    "rating": float(games.get("rating")) if games.get("rating") else None,
                    "goals": goals.get("total"),
                    "assists": goals.get("assists"),
                    "shots_total": stat.get("shots", {}).get("total"),
                    "shots_on": stat.get("shots", {}).get("on"),
                    "passes_total": passes.get("total"),
                    "passes_key": passes.get("key"),
                    "passes_accuracy": passes.get("accuracy"),
                    "yellow_cards": cards.get("yellow"),
                    "red_cards": cards.get("red"),
                    "duels_total": duels.get("total"),
                    "duels_won": duels.get("won"),
                    "tackles_total": tackles.get("total"),
                    "interceptions": tackles.get("interceptions"),
                })

        return pd.DataFrame(rows)
