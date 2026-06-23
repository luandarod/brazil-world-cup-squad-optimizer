from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.espn_client import ESPNClient, normalize_completed_events, normalize_unplayed_events


def test_normalize_completed_events_keeps_completed_matches_only() -> None:
    payload = {
        "events": [
            {
                "id": "401",
                "date": "2026-06-11T19:00Z",
                "name": "Brazil vs Mexico",
                "status": {
                    "type": {
                        "completed": True,
                        "description": "Final",
                        "detail": "FT",
                    }
                },
                "competitions": [
                    {
                        "altGameNote": "FIFA World Cup, Group A",
                        "status": {
                            "type": {
                                "completed": True,
                                "description": "Final",
                                "detail": "FT",
                            }
                        },
                        "type": {"abbreviation": "GROUP"},
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "3",
                                "team": {"displayName": "Brazil"},
                                "statistics": [{"name": "totalShots", "displayValue": "14"}],
                            },
                            {
                                "homeAway": "away",
                                "score": "1",
                                "team": {"displayName": "Mexico"},
                                "statistics": [{"name": "totalShots", "displayValue": "7"}],
                            },
                        ],
                    }
                ],
            },
            {
                "id": "402",
                "date": "2026-06-11T22:00Z",
                "name": "Argentina vs Canada",
                "status": {
                    "type": {
                        "completed": False,
                        "description": "Scheduled",
                        "detail": "7:00 PM",
                    }
                },
                "competitions": [
                    {
                        "status": {
                            "type": {
                                "completed": False,
                                "description": "Scheduled",
                                "detail": "7:00 PM",
                            }
                        },
                        "type": {"abbreviation": "GROUP"},
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "0",
                                "team": {"displayName": "Argentina"},
                            },
                            {
                                "homeAway": "away",
                                "score": "0",
                                "team": {"displayName": "Canada"},
                            },
                        ],
                    }
                ],
            },
        ]
    }

    rows = normalize_completed_events(payload, retrieved_at="2026-06-16T12:00:00Z")

    assert rows == [
        {
            "match_id": "401",
            "match_date": "2026-06-11",
            "stage": "Group A",
            "home_team": "Brazil",
            "home_team_id": None,
            "away_team": "Mexico",
            "away_team_id": None,
            "home_goals": 3,
            "away_goals": 1,
            "home_shots": 14,
            "away_shots": 7,
            "home_cards": None,
            "away_cards": None,
            "home_fouls": None,
            "away_fouls": None,
            "status": "Final",
            "source": "espn",
            "source_retrieved_at": "2026-06-16T12:00:00Z",
        }
    ]


def test_fetch_completed_matches_for_date_passes_ssl_verification_flag() -> None:
    calls: list[dict] = []

    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "events": [
                    {
                        "id": "777",
                        "date": "2026-06-12T19:00Z",
                        "status": {"type": {"completed": True, "description": "Final", "detail": "FT"}},
                        "competitions": [
                            {
                                "status": {
                                    "type": {"completed": True, "description": "Final", "detail": "FT"}
                                },
                                "type": {"abbreviation": "R16"},
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "score": "2",
                                        "team": {"displayName": "Spain"},
                                        "statistics": [{"name": "totalShots", "displayValue": "11"}],
                                    },
                                    {
                                        "homeAway": "away",
                                        "score": "0",
                                        "team": {"displayName": "Japan"},
                                        "statistics": [{"name": "totalShots", "displayValue": "5"}],
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }

    class StubSession:
        def get(self, url: str, *, params: dict, timeout: int, verify: bool):  # noqa: ANN002
            calls.append(
                {
                    "url": url,
                    "params": params,
                    "timeout": timeout,
                    "verify": verify,
                }
            )
            return StubResponse()

    client = ESPNClient(session=StubSession(), verify_ssl=False, timeout=12)

    rows = client.fetch_completed_matches_for_date(date(2026, 6, 12))

    assert rows[0]["match_id"] == "777"
    assert calls == [
        {
            "url": ESPNClient.SCOREBOARD_URL,
            "params": {"dates": "20260612"},
            "timeout": 12,
            "verify": False,
        }
    ]


def test_normalize_unplayed_events_keeps_only_future_fixtures() -> None:
    payload = {
        "events": [
            {
                "id": "501",
                "date": "2026-06-24T19:00Z",
                "status": {"type": {"completed": False, "description": "Scheduled", "detail": "7:00 PM"}},
                "competitions": [
                    {
                        "altGameNote": "FIFA World Cup, Group A",
                        "status": {"type": {"completed": False, "description": "Scheduled", "detail": "7:00 PM"}},
                        "competitors": [
                            {"homeAway": "home", "team": {"displayName": "South Africa"}},
                            {"homeAway": "away", "team": {"displayName": "South Korea"}},
                        ],
                    }
                ],
            },
            {
                "id": "502",
                "date": "2026-06-24T22:00Z",
                "status": {"type": {"completed": True, "description": "Final", "detail": "FT"}},
                "competitions": [
                    {
                        "altGameNote": "FIFA World Cup, Group A",
                        "status": {"type": {"completed": True, "description": "Final", "detail": "FT"}},
                        "competitors": [
                            {"homeAway": "home", "score": "2", "team": {"displayName": "Mexico"}},
                            {"homeAway": "away", "score": "0", "team": {"displayName": "Czechia"}},
                        ],
                    }
                ],
            },
        ]
    }

    rows = normalize_unplayed_events(payload, retrieved_at="2026-06-20T12:00:00Z")

    assert rows == [
        {
            "match_id": "501",
            "match_date": "2026-06-24",
            "stage": "Group A",
            "home_team": "South Africa",
            "home_team_id": None,
            "away_team": "South Korea",
            "away_team_id": None,
            "home_goals": None,
            "away_goals": None,
            "home_shots": None,
            "away_shots": None,
            "home_cards": None,
            "away_cards": None,
            "home_fouls": None,
            "away_fouls": None,
            "status": "Scheduled",
            "source": "espn",
            "source_retrieved_at": "2026-06-20T12:00:00Z",
        }
    ]


def test_fetch_matches_for_date_passes_ssl_verification_flag() -> None:
    calls: list[dict] = []

    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "events": [
                    {
                        "id": "888",
                        "date": "2026-06-24T19:00Z",
                        "status": {"type": {"completed": False, "description": "Scheduled", "detail": "7:00 PM"}},
                        "competitions": [
                            {
                                "altGameNote": "FIFA World Cup, Group A",
                                "status": {
                                    "type": {"completed": False, "description": "Scheduled", "detail": "7:00 PM"}
                                },
                                "competitors": [
                                    {"homeAway": "home", "team": {"displayName": "South Africa"}},
                                    {"homeAway": "away", "team": {"displayName": "South Korea"}},
                                ],
                            }
                        ],
                    }
                ]
            }

    class StubSession:
        def get(self, url: str, *, params: dict, timeout: int, verify: bool):  # noqa: ANN002
            calls.append(
                {
                    "url": url,
                    "params": params,
                    "timeout": timeout,
                    "verify": verify,
                }
            )
            return StubResponse()

    client = ESPNClient(session=StubSession(), verify_ssl=False, timeout=8)

    rows = client.fetch_matches_for_date(date(2026, 6, 24))

    assert rows[0]["match_id"] == "888"
    assert rows[0]["home_goals"] is None
    assert calls == [
        {
            "url": ESPNClient.SCOREBOARD_URL,
            "params": {"dates": "20260624"},
            "timeout": 8,
            "verify": False,
        }
    ]
