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

    def fetch_matches_for_date(self, match_date: date) -> list[dict]:
        response = self.session.get(
            self.SCOREBOARD_URL,
            params={"dates": match_date.strftime("%Y%m%d")},
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return normalize_unplayed_events(response.json(), retrieved_at=retrieved_at)


def normalize_completed_events(payload: dict[str, Any], retrieved_at: str) -> list[dict]:
    rows: list[dict] = []
    for event in payload.get("events", []):
        normalized = _normalize_event(event, retrieved_at, require_completed=True)
        if normalized is not None:
            rows.append(normalized)
    return rows


def normalize_unplayed_events(payload: dict[str, Any], retrieved_at: str) -> list[dict]:
    rows: list[dict] = []
    for event in payload.get("events", []):
        normalized = _normalize_event(event, retrieved_at, require_completed=False)
        if normalized is not None:
            rows.append(normalized)
    return rows


def _normalize_event(
    event: dict[str, Any],
    retrieved_at: str,
    *,
    require_completed: bool,
) -> dict | None:
    competition = _first_competition(event)
    if competition is None:
        return None

    is_completed = _is_completed(event, competition)
    if require_completed and not is_completed:
        return None
    if not require_completed and is_completed:
        return None

    home_team = _find_competitor(competition, "home", is_completed=is_completed)
    away_team = _find_competitor(competition, "away", is_completed=is_completed)
    if home_team is None or away_team is None:
        return None

    match_id = event.get("id")
    match_date = str(event.get("date", ""))[:10]
    if not match_id or not match_date:
        return None

    home_cards = home_team["cards"]
    away_cards = away_team["cards"]
    if is_completed and "details" in competition:
        home_cards = 0
        away_cards = 0
        details = competition.get("details") or []
        home_id = str(home_team["team_id"]) if home_team["team_id"] is not None else None
        away_id = str(away_team["team_id"]) if away_team["team_id"] is not None else None
        for detail in details:
            if detail.get("yellowCard") or detail.get("redCard"):
                detail_team = detail.get("team") or {}
                detail_team_id = str(detail_team.get("id")) if detail_team.get("id") is not None else None
                if detail_team_id:
                    if detail_team_id == home_id:
                        home_cards += 1
                    elif detail_team_id == away_id:
                        away_cards += 1

    return {
        "match_id": str(match_id),
        "match_date": match_date,
        "stage": _read_stage(event, competition),
        "home_team": home_team["team"],
        "home_team_id": home_team["team_id"],
        "away_team": away_team["team"],
        "away_team_id": away_team["team_id"],
        "home_goals": home_team["score"],
        "away_goals": away_team["score"],
        "home_shots": home_team["shots"],
        "away_shots": away_team["shots"],
        "home_cards": home_cards,
        "away_cards": away_cards,
        "home_fouls": home_team["fouls"],
        "away_fouls": away_team["fouls"],
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


def _find_competitor(
    competition: dict[str, Any],
    home_away: str,
    *,
    is_completed: bool,
) -> dict | None:
    for competitor in competition.get("competitors", []):
        if competitor.get("homeAway") != home_away:
            continue
        team = competitor.get("team") or {}
        team_name = team.get("displayName") or team.get("shortDisplayName") or team.get("name")
        if not team_name:
            return None
        statistics = competitor.get("statistics") or []
        score: int | None = None
        if is_completed:
            raw_score = competitor.get("score")
            if raw_score is None:
                return None
            score = int(raw_score)
        return {
            "team": str(team_name),
            "team_id": str(team.get("id")) if team.get("id") is not None else None,
            "score": score,
            "shots": _read_stat_value(statistics, "totalShots") if is_completed else None,
            "fouls": _read_stat_value(statistics, "foulsCommitted") if is_completed else None,
            "cards": _read_cards_value(statistics) if is_completed else None,
        }
    return None


def _read_stat_value(statistics: list[dict[str, Any]], target_name: str) -> int | None:
    for statistic in statistics:
        if statistic.get("name") != target_name:
            continue
        value = statistic.get("displayValue")
        if value is None:
            return None
        try:
            return int(float(str(value)))
        except ValueError:
            return None
    return None


def _read_cards_value(statistics: list[dict[str, Any]]) -> int | None:
    yellow_cards = _read_stat_value(statistics, "yellowCards")
    red_cards = _read_stat_value(statistics, "redCards")
    if yellow_cards is None and red_cards is None:
        return None
    return int((yellow_cards or 0) + (red_cards or 0))


def _read_stage(event: dict[str, Any], competition: dict[str, Any]) -> str:
    alt_game_note = competition.get("altGameNote")
    if isinstance(alt_game_note, str) and "," in alt_game_note:
        return alt_game_note.split(",", 1)[1].strip()

    season = event.get("season") or {}
    if isinstance(season, dict):
        season_slug = season.get("slug")
        if season_slug:
            return str(season_slug).replace("-", " ").title()

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
