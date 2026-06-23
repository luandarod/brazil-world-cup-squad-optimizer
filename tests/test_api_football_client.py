from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.api_football_client import APIFootballClient


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class _FakeSession:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.calls: list[dict] = []

    def get(self, url: str, headers: dict, params: dict, timeout: int) -> _FakeResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return _FakeResponse(self.payloads.pop(0))


def test_api_football_client_requires_local_secret() -> None:
    try:
        APIFootballClient(api_key="")
    except ValueError as exc:
        assert "API_FOOTBALL_KEY" in str(exc)
    else:
        raise AssertionError("Expected a missing-key error.")


def test_api_football_client_paginates_and_flattens_team_player_stats() -> None:
    session = _FakeSession(
        [
            {
                "paging": {"current": 1, "total": 2},
                "response": [
                    {
                        "player": {"id": 10, "name": "Player One"},
                        "statistics": [
                            {
                                "team": {"name": "Brazil"},
                                "games": {
                                    "position": "Attacker",
                                    "appearences": 12,
                                    "minutes": 900,
                                    "substitutes": {"in": 2},
                                },
                                "goals": {"total": 5, "assists": 1},
                                "shots": {"total": 18, "on": 9},
                                "cards": {"yellow": 2, "red": 0},
                                "fouls": {"committed": 7, "drawn": 10},
                            }
                        ],
                    }
                ],
            },
            {
                "paging": {"current": 2, "total": 2},
                "response": [
                    {
                        "player": {"id": 20, "name": "Player Two"},
                        "statistics": [
                            {
                                "team": {"name": "Brazil"},
                                "games": {
                                    "position": "Midfielder",
                                    "appearences": 8,
                                    "minutes": 620,
                                    "substitutes": {"in": 4},
                                },
                                "goals": {"total": 2, "assists": 3},
                                "shots": {"total": 10, "on": 4},
                                "cards": {"yellow": 1, "red": 1},
                                "fouls": {"committed": 11, "drawn": 6},
                            }
                        ],
                    }
                ],
            },
        ]
    )
    client = APIFootballClient(api_key="test-key", session=session)

    rows = client.fetch_team_recent_player_stats(team_id=1, season=2025, team_name="Brasil")

    assert len(rows) == 2
    assert rows[0]["team"] == "Brasil"
    assert rows[0]["total_goals"] == 5.0
    assert rows[0]["total_shots"] == 18.0
    assert rows[0]["fouls_committed"] == 7.0
    assert rows[1]["red_cards"] == 1.0
    assert session.calls[0]["params"]["page"] == 1
    assert session.calls[1]["params"]["page"] == 2


def test_api_football_client_team_search_prefers_normalized_exact_match() -> None:
    session = _FakeSession(
        [
            {
                "response": [
                    {"team": {"id": 2, "name": "Brasil"}},
                    {"team": {"id": 3, "name": "Brazil"}},
                ]
            }
        ]
    )
    client = APIFootballClient(api_key="test-key", session=session)

    team = client.search_team("Brazil")

    assert team == {"id": 3, "name": "Brazil"}
