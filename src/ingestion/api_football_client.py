from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from src.config import API_FOOTBALL_HOST, API_FOOTBALL_KEY, API_FOOTBALL_PRIOR_SEASON


class APIFootballClient:
    def __init__(
        self,
        api_key: str | None = None,
        host: str = API_FOOTBALL_HOST,
        session: requests.Session | None = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = API_FOOTBALL_KEY if api_key is None else api_key
        if not self.api_key:
            raise ValueError("API_FOOTBALL_KEY not found. Configure a local .env or .env.local file.")

        self.host = host
        self.base_url = f"https://{self.host}"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
        }

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.headers,
            params=params or {},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def search_team(self, team_name: str) -> dict[str, Any] | None:
        payload = self.get("/teams", {"search": team_name})
        for item in payload.get("response", []):
            team = item.get("team") or {}
            if _normalize_text(team.get("name")) == _normalize_text(team_name):
                return team

        response_rows = payload.get("response", [])
        if not response_rows:
            return None
        return response_rows[0].get("team")

    def fetch_team_recent_player_stats(
        self,
        team_id: str | int,
        season: int = API_FOOTBALL_PRIOR_SEASON,
        team_name: str | None = None,
    ) -> list[dict[str, Any]]:
        page = 1
        rows: list[dict[str, Any]] = []
        while True:
            payload = self.get(
                "/players",
                {
                    "team": team_id,
                    "season": season,
                    "page": page,
                },
            )
            rows.extend(_flatten_player_rows(payload.get("response", []), team_name=team_name))
            paging = payload.get("paging") or {}
            total_pages = int(paging.get("total") or 1)
            if page >= total_pages:
                break
            page += 1
        return rows

    def search_player(self, player_name: str, season: int = API_FOOTBALL_PRIOR_SEASON) -> pd.DataFrame:
        payload = self.get("/players", {"search": player_name, "season": season})
        return pd.DataFrame(_flatten_player_rows(payload.get("response", [])))


def _flatten_player_rows(
    response_rows: list[dict[str, Any]],
    *,
    team_name: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in response_rows:
        player = item.get("player") or {}
        statistics = item.get("statistics") or []
        aggregate = {
            "team": team_name,
            "player_id": str(player.get("id") or ""),
            "player_name": player.get("name"),
            "position": None,
            "appearances": 0.0,
            "sub_ins": 0.0,
            "minutes": 0.0,
            "total_goals": 0.0,
            "total_shots": 0.0,
            "shots_on_target": 0.0,
            "goal_assists": 0.0,
            "yellow_cards": 0.0,
            "red_cards": 0.0,
            "fouls_committed": 0.0,
            "fouls_suffered": 0.0,
            "source": "api-football",
        }
        for stat in statistics:
            games = stat.get("games") or {}
            team = stat.get("team") or {}
            goals = stat.get("goals") or {}
            shots = stat.get("shots") or {}
            cards = stat.get("cards") or {}
            fouls = stat.get("fouls") or {}

            aggregate["team"] = aggregate["team"] or team.get("name")
            aggregate["position"] = aggregate["position"] or games.get("position")
            aggregate["appearances"] += _to_float(games.get("appearences"))
            aggregate["sub_ins"] += _to_float((games.get("substitutes") or {}).get("in"))
            aggregate["minutes"] += _to_float(games.get("minutes"))
            aggregate["total_goals"] += _to_float(goals.get("total"))
            aggregate["total_shots"] += _to_float(shots.get("total"))
            aggregate["shots_on_target"] += _to_float(shots.get("on"))
            aggregate["goal_assists"] += _to_float(goals.get("assists"))
            aggregate["yellow_cards"] += _to_float(cards.get("yellow"))
            aggregate["red_cards"] += _to_float(cards.get("red"))
            aggregate["fouls_committed"] += _to_float(fouls.get("committed"))
            aggregate["fouls_suffered"] += _to_float(fouls.get("drawn"))
        rows.append(aggregate)
    return rows


def _to_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _normalize_text(value: object) -> str:
    return "".join(char.lower() for char in str(value or "") if char.isalnum())
