from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


class ESPNRosterClient:
    ROSTER_URL_TEMPLATE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{team_id}/roster"

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    def fetch_team_roster(self, team_id: str, team_name: str | None = None) -> list[dict[str, Any]]:
        response = self.session.get(
            self.ROSTER_URL_TEMPLATE.format(team_id=team_id),
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = response.json()
        athletes = payload.get("athletes") or []
        rows: list[dict[str, Any]] = []
        for athlete in athletes:
            if not isinstance(athlete, dict):
                continue
            team_block = athlete.get("defaultTeam") or payload.get("team") or {}
            rows.append(
                {
                    "team_id": str(team_id),
                    "team": team_name
                    or team_block.get("displayName")
                    or team_block.get("shortDisplayName")
                    or team_block.get("name"),
                    "player_id": str(athlete.get("id") or ""),
                    "player_name": athlete.get("displayName") or athlete.get("fullName") or athlete.get("shortName"),
                    "position": (athlete.get("position") or {}).get("displayName"),
                    "appearances": _read_athlete_stat(athlete, "appearances"),
                    "sub_ins": _read_athlete_stat(athlete, "subIns"),
                    "total_goals": _read_athlete_stat(athlete, "totalGoals"),
                    "total_shots": _read_athlete_stat(athlete, "totalShots"),
                    "shots_on_target": _read_athlete_stat(athlete, "shotsOnTarget"),
                    "goal_assists": _read_athlete_stat(athlete, "goalAssists"),
                    "yellow_cards": _read_athlete_stat(athlete, "yellowCards"),
                    "red_cards": _read_athlete_stat(athlete, "redCards"),
                    "fouls_committed": _read_athlete_stat(athlete, "foulsCommitted"),
                    "fouls_suffered": _read_athlete_stat(athlete, "foulsSuffered"),
                    "retrieved_at": retrieved_at,
                }
            )
        return rows


def _read_athlete_stat(athlete: dict[str, Any], stat_name: str) -> float:
    statistics = athlete.get("statistics") or {}
    splits = statistics.get("splits") or {}
    for category in splits.get("categories") or []:
        if not isinstance(category, dict):
            continue
        for stat in category.get("stats") or []:
            if stat.get("name") != stat_name:
                continue
            value = stat.get("value")
            if value is None:
                return 0.0
            return float(value)
    return 0.0
