from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import requests


class ESPNClient:
    SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    def fetch_completed_matches_for_date(self, match_date: date) -> list[dict]:
        response = self.session.get(
            self.SCOREBOARD_URL,
            params={"dates": match_date.strftime("%Y%m%d")},
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return normalize_completed_events(response.json(), retrieved_at=retrieved_at)


def normalize_completed_events(payload: dict[str, Any], retrieved_at: str) -> list[dict]:
    rows: list[dict] = []
    for event in payload.get("events", []):
        normalized = _normalize_completed_event(event, retrieved_at)
        if normalized is not None:
            rows.append(normalized)
    return rows


def _normalize_completed_event(event: dict[str, Any], retrieved_at: str) -> dict | None:
    competition = _first_competition(event)
    if competition is None or not _is_completed(event, competition):
        return None

    home_team = _find_competitor(competition, "home")
    away_team = _find_competitor(competition, "away")
    if home_team is None or away_team is None:
        return None

    match_id = event.get("id")
    match_date = str(event.get("date", ""))[:10]
    if not match_id or not match_date:
        return None

    return {
        "match_id": str(match_id),
        "match_date": match_date,
        "stage": _read_stage(competition),
        "home_team": home_team["team"],
        "away_team": away_team["team"],
        "home_goals": home_team["score"],
        "away_goals": away_team["score"],
        "status": _read_status(event, competition),
        "source": "espn",
        "source_retrieved_at": retrieved_at,
    }


def _first_competition(event: dict[str, Any]) -> dict[str, Any] | None:
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    first = competitions[0]
    if not isinstance(first, dict):
        return None
    return first


def _is_completed(event: dict[str, Any], competition: dict[str, Any]) -> bool:
    status = competition.get("status") or event.get("status") or {}
    if not isinstance(status, dict):
        return False
    status_type = status.get("type") or {}
    if not isinstance(status_type, dict):
        return False
    return bool(status_type.get("completed"))


def _find_competitor(competition: dict[str, Any], home_away: str) -> dict | None:
    for competitor in competition.get("competitors", []):
        if competitor.get("homeAway") != home_away:
            continue
        team = competitor.get("team") or {}
        team_name = team.get("displayName") or team.get("shortDisplayName") or team.get("name")
        if not team_name:
            return None
        score = competitor.get("score")
        if score is None:
            return None
        return {"team": str(team_name), "score": int(score)}
    return None


def _read_stage(competition: dict[str, Any]) -> str:
    competition_type = competition.get("type") or {}
    if isinstance(competition_type, dict):
        stage = competition_type.get("abbreviation") or competition_type.get("shortDetail")
        if stage:
            return str(stage)
    status = competition.get("status") or {}
    if isinstance(status, dict):
        stage = status.get("period")
        if stage:
            return str(stage)
    return "unknown"


def _read_status(event: dict[str, Any], competition: dict[str, Any]) -> str:
    for candidate in (competition.get("status"), event.get("status")):
        if not isinstance(candidate, dict):
            continue
        status_type = candidate.get("type") or {}
        if not isinstance(status_type, dict):
            continue
        for key in ("description", "detail", "name"):
            value = status_type.get(key)
            if value:
                return str(value)
    return "Final"

