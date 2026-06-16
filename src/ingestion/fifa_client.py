from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import requests


class FIFAClient:
    """Fetch official FIFA World Cup pages and extract completed-match payloads."""

    BASE_URL = (
        "https://www.fifa.com/en/tournaments/mens/worldcup/"
        "canadamexicousa2026/scores-fixtures"
    )
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
    }

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 30,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_world_cup_matches(self) -> list[dict]:
        response = self.session.get(
            self.BASE_URL,
            headers=self.DEFAULT_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()

        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return extract_match_payloads_from_page(response.text, retrieved_at=retrieved_at)


def extract_match_payloads_from_page(html: str, retrieved_at: str) -> list[dict]:
    """Extract normalized match payloads from FIFA page JSON when discoverable."""
    for candidate in _extract_json_blobs(html):
        matches = _find_matches(candidate, retrieved_at)
        if matches:
            return matches
    return []


def _extract_json_blobs(html: str) -> list[Any]:
    blobs: list[Any] = []

    for match in re.finditer(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    ):
        try:
            blobs.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue

    for match in re.finditer(
        r"<script[^>]*>\s*(\{.*?\})\s*</script>",
        html,
        re.DOTALL,
    ):
        try:
            blobs.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue

    return blobs


def _find_matches(payload: Any, retrieved_at: str) -> list[dict]:
    matches: list[dict] = []
    for candidate in _walk_dicts(payload):
        normalized = _normalize_match(candidate, retrieved_at)
        if normalized is not None:
            matches.append(normalized)
    return matches


def _walk_dicts(payload: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        items.append(payload)
        for value in payload.values():
            items.extend(_walk_dicts(value))
    elif isinstance(payload, list):
        for value in payload:
            items.extend(_walk_dicts(value))
    return items


def _normalize_match(candidate: dict[str, Any], retrieved_at: str) -> dict | None:
    home_team = _normalize_team(candidate.get("homeTeam") or candidate.get("home_team"))
    away_team = _normalize_team(candidate.get("awayTeam") or candidate.get("away_team"))
    if home_team is None or away_team is None:
        return None

    match_id = candidate.get("id") or candidate.get("matchId")
    match_date = (
        candidate.get("date")
        or candidate.get("utcDate")
        or candidate.get("localDate")
        or candidate.get("kickOff")
    )
    if not match_id or not match_date:
        return None

    return {
        "id": str(match_id),
        "date": str(match_date)[:10],
        "stage": candidate.get("stage") or candidate.get("competitionPhase") or "unknown",
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": None,
        "shooting_source": None,
        "retrieved_at": retrieved_at,
        "home_team": home_team,
        "away_team": away_team,
    }


def _normalize_team(team_payload: Any) -> dict | None:
    if not isinstance(team_payload, dict):
        return None

    name = team_payload.get("name") or team_payload.get("teamName") or team_payload.get("shortName")
    if not name:
        return None

    goals = _read_metric(team_payload, ["goals", "score", "goalsFor"])
    cards = _read_metric(team_payload, ["cards", "yellowCards", "disciplineCards"])
    shots = _read_metric(team_payload, ["shots", "shotsTotal"])

    return {
        "name": name,
        "goals": goals,
        "cards": cards,
        "shots": shots,
    }


def _read_metric(team_payload: dict[str, Any], keys: list[str]) -> int | None:
    for key in keys:
        value = team_payload.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None
