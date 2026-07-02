from __future__ import annotations
import re
from datetime import date, datetime, timedelta
from typing import Iterable
import pandas as pd

from src.ingestion.espn_client import ESPNClient
from src.ingestion.fifa_client import FIFAClient
from src.ingestion.lineup_client import LineupClient
from src.domain.match_schema import PublicMatchTruthRow

TOURNAMENT_FINAL_DATE = "2026-07-19"

PUBLIC_MATCH_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "home_shots",
    "away_shots",
    "home_cards",
    "away_cards",
    "home_fouls",
    "away_fouls",
    "status",
    "source",
    "source_retrieved_at",
    "is_future_fixture",
    "home_lineup_confirmed",
    "away_lineup_confirmed",
    "home_probable_lineup_count",
    "away_probable_lineup_count",
    "home_substitutions_used",
    "away_substitutions_used",
]

def _load_normalized_matches(
    start_date: str,
    end_date: str,
    client: ESPNClient | None,
    disable_ssl_verification: bool,
) -> list[dict]:
    if client is not None:
        return _fetch_completed_matches(client, start_date, end_date)

    fifa_matches = _fetch_fifa_matches(start_date, end_date)
    if fifa_matches:
        return fifa_matches

    espn_client = ESPNClient(verify_ssl=not disable_ssl_verification)
    return _fetch_completed_matches(espn_client, start_date, end_date)



def _load_future_fixtures(
    start_date: str,
    end_date: str,
    schedule_client: object | None,
) -> list[dict]:
    if schedule_client is None:
        return []

    rows: list[dict] = []
    for match_date in _iter_dates(start_date, end_date):
        rows.extend(schedule_client.fetch_matches_for_date(match_date))
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows



def _fetch_completed_matches(client: ESPNClient, start_date: str, end_date: str) -> list[dict]:
    rows: list[dict] = []
    for match_date in _iter_dates(start_date, end_date):
        rows.extend(client.fetch_completed_matches_for_date(match_date))
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows



def _iter_dates(start_date: str, end_date: str) -> Iterable[date]:
    current = _parse_date(start_date)
    finish = _parse_date(end_date)
    while current <= finish:
        yield current
        current += timedelta(days=1)



def _fetch_fifa_matches(start_date: str, end_date: str) -> list[dict]:
    try:
        raw_matches = FIFAClient().fetch_world_cup_matches()
    except Exception:
        return []

    start = _parse_date(start_date)
    finish = _parse_date(end_date)
    rows: list[dict] = []
    for raw_match in raw_matches:
        match_day = _parse_date(str(raw_match.get("date", ""))[:10])
        if match_day < start or match_day > finish:
            continue
        rows.append(
            {
                "match_id": raw_match["id"],
                "match_date": raw_match["date"],
                "stage": raw_match["stage"],
                "home_team": raw_match["home_team"]["name"],
                "away_team": raw_match["away_team"]["name"],
                "home_goals": raw_match["home_team"]["goals"],
                "away_goals": raw_match["away_team"]["goals"],
                "home_shots": raw_match["home_team"].get("shots"),
                "away_shots": raw_match["away_team"].get("shots"),
                "home_cards": raw_match["home_team"].get("cards"),
                "away_cards": raw_match["away_team"].get("cards"),
                "home_fouls": raw_match["home_team"].get("fouls"),
                "away_fouls": raw_match["away_team"].get("fouls"),
                "status": "Final",
                "source": raw_match.get("source", "fifa"),
                "source_retrieved_at": raw_match.get("retrieved_at"),
            }
        )
    rows.sort(key=lambda row: (row["match_date"], row["match_id"]))
    return rows



def _build_public_match_frame(rows: list[dict], is_future_fixture: bool) -> pd.DataFrame:
    normalized_rows = []
    allowed_keys = set(PUBLIC_MATCH_COLUMNS)
    for row in rows:
        payload = {key: value for key, value in dict(row).items() if key in allowed_keys}
        payload.setdefault("is_future_fixture", is_future_fixture)
        normalized_rows.append(
            PublicMatchTruthRow(**payload).model_dump()
        )
    return pd.DataFrame(normalized_rows, columns=PUBLIC_MATCH_COLUMNS)



def _attach_player_context(frame: pd.DataFrame, lineup_client: LineupClient) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    context_rows = []
    for match_id in frame["match_id"].astype(str):
        context = lineup_client.fetch_match_player_context(match_id)
        context_rows.append({"match_id": match_id, **context})

    context_frame = pd.DataFrame(
        context_rows,
        columns=[
            "match_id",
            "home_lineup_confirmed",
            "away_lineup_confirmed",
            "home_probable_lineup_count",
            "away_probable_lineup_count",
            "home_substitutions_used",
            "away_substitutions_used",
        ],
    )
    merged = frame.copy()
    merged["match_id"] = merged["match_id"].astype(str)
    merged = merged.drop(
        columns=[
            "home_lineup_confirmed",
            "away_lineup_confirmed",
            "home_probable_lineup_count",
            "away_probable_lineup_count",
            "home_substitutions_used",
            "away_substitutions_used",
        ]
    ).merge(context_frame, on="match_id", how="left")
    return merged[PUBLIC_MATCH_COLUMNS]



def _rows_have_team_ids(rows: list[dict]) -> bool:
    for row in rows:
        if row.get("home_team_id") or row.get("away_team_id"):
            return True
    return False



def _normalize_team_name(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    aliases = {
        "bosnia herzegovina": "bosnia herzegovina",
        "cape verde": "cape verde",
        "congo dr": "congo dr",
        "czech republic": "czechia",
        "czechia": "czechia",
        "curacao": "curacao",
        "ivory coast": "ivory coast",
        "korea republic": "south korea",
        "korea south": "south korea",
        "mexico": "mexico",
        "morocco": "morocco",
        "netherlands": "netherlands",
        "saudi arabia": "saudi arabia",
        "south korea": "south korea",
        "turkey": "turkiye",
        "turkiye": "turkiye",
        "united states": "united states",
        "usa": "united states",
    }
    return aliases.get(text, text)



def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()



