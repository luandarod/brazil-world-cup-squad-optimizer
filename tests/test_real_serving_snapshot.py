from pathlib import Path
import sys
import tempfile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipelines.build_real_serving_snapshot import (
    _resolve_team_label,
    build_real_serving_snapshot,
)
from src.serving.load_outputs import (
    read_coverage_summary,
    read_group_forecast_summary,
    read_match_predictions,
    read_match_prediction_vs_actual,
    read_methodology_status,
    read_model_leaderboard,
    read_knockout_forecast_summary,
    read_observed_match_results,
    read_team_forecast_summary,
    read_team_summary,
    read_title_probability_summary,
    read_top_scorer_forecast,
)


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="real-serving-snapshot-"))


def test_build_real_serving_snapshot_writes_honest_outputs() -> None:
    class StubClient:
        def fetch_completed_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-11":
                return [
                    {
                        "match_id": "401",
                        "match_date": "2026-06-11",
                        "stage": "Group A",
                        "home_team": "Brazil",
                        "away_team": "Mexico",
                        "home_goals": 3,
                        "away_goals": 1,
                        "home_shots": 14,
                        "away_shots": 7,
                        "status": "Final",
                        "source": "espn",
                        "source_retrieved_at": "2026-06-16T12:00:00Z",
                    }
                ]
            if str(match_date) == "2026-06-12":
                return [
                    {
                        "match_id": "402",
                        "match_date": "2026-06-12",
                        "stage": "Group A",
                        "home_team": "Canada",
                        "away_team": "Brazil",
                        "home_goals": 0,
                        "away_goals": 2,
                        "home_shots": 6,
                        "away_shots": 10,
                        "status": "Final",
                        "source": "espn",
                        "source_retrieved_at": "2026-06-16T12:00:00Z",
                    }
                ]
            return []

    class StubScheduleClient:
        def fetch_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-13":
                return [
                    {
                        "match_id": "403",
                        "match_date": "2026-06-13",
                        "stage": "Group A",
                        "home_team": "Brazil",
                        "away_team": "Canada",
                        "status": "Scheduled",
                        "source": "fifa",
                    }
                ]
            if str(match_date) == "2026-06-14":
                return [
                    {
                        "match_id": "404",
                        "match_date": "2026-06-14",
                        "stage": "Quarterfinal",
                        "home_team": "Argentina",
                        "away_team": "France",
                        "status": "Scheduled",
                        "source": "fifa",
                    }
                ]
            return []

    serving_dir = _make_temp_dir() / "serving"
    outputs = build_real_serving_snapshot(
        start_date="2026-06-11",
        end_date="2026-06-14",
        output_dir=serving_dir,
        client=StubClient(),
        schedule_client=StubScheduleClient(),
    )

    assert set(outputs.keys()) == {
        "observed_results",
        "future_fixtures",
        "coverage",
        "teams",
        "leaderboard",
        "predictions",
        "match_prediction_vs_actual",
        "group_forecast_summary",
        "knockout_forecast_summary",
        "team_forecast_summary",
        "methodology_status",
        "title_probability_summary",
        "top_scorer_forecast",
    }
    assert outputs["future_fixtures"]["match_id"].tolist() == ["403", "404"]

    observed = read_observed_match_results(serving_dir)
    assert list(observed.columns) == [
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
    observed_without_cards = observed.drop(columns=["home_cards", "away_cards", "home_fouls", "away_fouls"]).to_dict("records")
    assert observed_without_cards == [
        {
            "match_id": 401,
            "match_date": "2026-06-11",
            "stage": "Group A",
            "home_team": "Brazil",
            "away_team": "Mexico",
            "home_goals": 3,
            "away_goals": 1,
            "home_shots": 14,
            "away_shots": 7,
            "status": "Final",
            "source": "espn",
            "source_retrieved_at": "2026-06-16T12:00:00Z",
            "is_future_fixture": False,
            "home_lineup_confirmed": False,
            "away_lineup_confirmed": False,
            "home_probable_lineup_count": 0,
            "away_probable_lineup_count": 0,
            "home_substitutions_used": 0,
            "away_substitutions_used": 0,
        },
        {
            "match_id": 402,
            "match_date": "2026-06-12",
            "stage": "Group A",
            "home_team": "Canada",
            "away_team": "Brazil",
            "home_goals": 0,
            "away_goals": 2,
            "home_shots": 6,
            "away_shots": 10,
            "status": "Final",
            "source": "espn",
            "source_retrieved_at": "2026-06-16T12:00:00Z",
            "is_future_fixture": False,
            "home_lineup_confirmed": False,
            "away_lineup_confirmed": False,
            "home_probable_lineup_count": 0,
            "away_probable_lineup_count": 0,
            "home_substitutions_used": 0,
            "away_substitutions_used": 0,
        },
    ]
    assert observed["home_cards"].isna().all()
    assert observed["away_cards"].isna().all()
    assert observed["home_fouls"].isna().all()
    assert observed["away_fouls"].isna().all()

    coverage = read_coverage_summary(serving_dir)
    assert coverage["metric_name"].tolist() == ["goals", "cards", "fouls", "shots"]
    assert coverage.loc[coverage["metric_name"] == "goals", "coverage_pct"].iloc[0] == 100.0
    assert coverage.loc[coverage["metric_name"] == "shots", "coverage_pct"].iloc[0] == 100.0
    assert coverage.loc[coverage["metric_name"] == "fouls", "coverage_pct"].iloc[0] == 0.0

    teams = read_team_summary(serving_dir)
    assert {"cards_for", "fouls_for"}.issubset(teams.columns)
    assert teams.loc[teams["team"] == "Brazil", "points"].iloc[0] == 6

    leaderboard = read_model_leaderboard(serving_dir)
    assert set(leaderboard["target_name"]) == {"goals_for", "shots_for"}
    assert not leaderboard.empty

    predictions = read_match_predictions(serving_dir).sort_values("match_id").reset_index(drop=True)
    assert {"predicted_home_cards", "predicted_home_fouls"}.issubset(predictions.columns)
    assert set(predictions["model_name"]) == {"hybrid-prior"}
    assert predictions.loc[predictions["match_id"] == 403, "predicted_home_goals"].iloc[0] > 0.5

    comparisons = read_match_prediction_vs_actual(serving_dir).sort_values("match_id").reset_index(drop=True)
    assert {"predicted_home_fouls", "actual_home_fouls", "winner_hit"}.issubset(comparisons.columns)
    assert comparisons["actual_winner"].tolist() == ["Brazil", "Brazil"]

    groups = read_group_forecast_summary(serving_dir).sort_values(["group_stage", "projected_total_points", "team"], ascending=[True, False, True]).reset_index(drop=True)
    assert groups.loc[0, "team"] == "Brazil"
    assert groups.loc[0, "projected_total_points"] == 9.0

    knockout = read_knockout_forecast_summary(serving_dir)
    assert {"predicted_home_shots", "predicted_home_cards", "predicted_home_fouls"}.issubset(knockout.columns)
    assert knockout.loc[0, "model_name"] == "hybrid-prior"

    team_forecasts = read_team_forecast_summary(serving_dir).sort_values("team").reset_index(drop=True)
    assert "forecast_total_points" in team_forecasts.columns
    assert "forecast_total_fouls_for" in team_forecasts.columns
    assert team_forecasts.loc[team_forecasts["team"] == "Brazil", "forecast_total_points"].iloc[0] == 9.0
    assert not read_title_probability_summary(serving_dir).empty
    assert read_top_scorer_forecast(serving_dir).empty

    methodology = read_methodology_status(serving_dir).sort_values("metric_name").reset_index(drop=True)
    assert methodology["metric_name"].tolist() == ["cards", "fouls", "goals", "shots"]
    assert methodology.loc[methodology["metric_name"] == "cards", "publish_status"].iloc[0] == "forecast-only"
    assert methodology.loc[methodology["metric_name"] == "goals", "publish_status"].iloc[0] == "published"


def test_build_real_serving_snapshot_returns_observed_and_future_match_inputs_with_player_context() -> None:
    class StubObservedClient:
        def fetch_completed_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-16":
                return [
                    {
                        "match_id": "760429",
                        "match_date": "2026-06-16",
                        "stage": "Group E",
                        "home_team": "Brazil",
                        "away_team": "Canada",
                        "home_goals": 2,
                        "away_goals": 0,
                        "home_shots": 15,
                        "away_shots": 8,
                        "home_cards": None,
                        "away_cards": None,
                        "status": "Final",
                        "source": "espn",
                        "source_retrieved_at": "2026-06-19T12:00:00Z",
                        "is_future_fixture": False,
                    }
                ]
            return []

    class StubScheduleClient:
        def fetch_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-16":
                return [
                    {
                        "match_id": "760430",
                        "match_date": "2026-06-16",
                        "stage": "Group F",
                        "home_team": "Japan",
                        "away_team": "Nigeria",
                        "status": "Scheduled",
                        "source": "fifa",
                    }
                ]
            return []

    class StubLineupClient:
        def fetch_match_player_context(self, match_id: str) -> dict:
            if match_id == "760429":
                return {
                    "home_lineup_confirmed": True,
                    "away_lineup_confirmed": True,
                    "home_probable_lineup_count": 11,
                    "away_probable_lineup_count": 11,
                    "home_substitutions_used": 5,
                    "away_substitutions_used": 4,
                }
            return {
                "home_lineup_confirmed": False,
                "away_lineup_confirmed": False,
                "home_probable_lineup_count": 11,
                "away_probable_lineup_count": 10,
                "home_substitutions_used": 0,
                "away_substitutions_used": 0,
            }

    serving_dir = _make_temp_dir() / "serving"
    outputs = build_real_serving_snapshot(
        start_date="2026-06-16",
        end_date="2026-06-16",
        output_dir=serving_dir,
        client=StubObservedClient(),
        schedule_client=StubScheduleClient(),
        lineup_client=StubLineupClient(),
    )

    assert set(outputs.keys()) == {
        "observed_results",
        "future_fixtures",
        "coverage",
        "teams",
        "leaderboard",
        "predictions",
        "match_prediction_vs_actual",
        "group_forecast_summary",
        "knockout_forecast_summary",
        "team_forecast_summary",
        "methodology_status",
        "title_probability_summary",
        "top_scorer_forecast",
    }
    assert outputs["observed_results"].to_dict("records") == [
        {
            "match_id": "760429",
            "match_date": "2026-06-16",
            "stage": "Group E",
            "home_team": "Brazil",
            "away_team": "Canada",
            "home_goals": 2,
            "away_goals": 0,
            "home_shots": 15,
            "away_shots": 8,
            "home_cards": None,
            "away_cards": None,
            "home_fouls": None,
            "away_fouls": None,
            "status": "Final",
            "source": "espn",
            "source_retrieved_at": "2026-06-19T12:00:00Z",
            "is_future_fixture": False,
            "home_lineup_confirmed": True,
            "away_lineup_confirmed": True,
            "home_probable_lineup_count": 11,
            "away_probable_lineup_count": 11,
            "home_substitutions_used": 5,
            "away_substitutions_used": 4,
        }
    ]
    assert outputs["future_fixtures"].to_dict("records") == [
        {
            "match_id": "760430",
            "match_date": "2026-06-16",
            "stage": "Group F",
            "home_team": "Japan",
            "away_team": "Nigeria",
            "home_goals": None,
            "away_goals": None,
            "home_shots": None,
            "away_shots": None,
            "home_cards": None,
            "away_cards": None,
            "home_fouls": None,
            "away_fouls": None,
            "status": "Scheduled",
            "source": "fifa",
            "source_retrieved_at": None,
            "is_future_fixture": True,
            "home_lineup_confirmed": False,
            "away_lineup_confirmed": False,
            "home_probable_lineup_count": 11,
            "away_probable_lineup_count": 10,
            "home_substitutions_used": 0,
            "away_substitutions_used": 0,
        }
    ]
    assert outputs["coverage"]["metric_name"].tolist() == ["goals", "cards", "fouls", "shots"]
    assert {"cards_for", "fouls_for"}.issubset(outputs["teams"].columns)
    assert not outputs["leaderboard"].empty
    assert not outputs["predictions"].empty
    assert not outputs["match_prediction_vs_actual"].empty
    assert not outputs["group_forecast_summary"].empty
    assert outputs["knockout_forecast_summary"].empty
    assert not outputs["team_forecast_summary"].empty
    assert outputs["methodology_status"]["metric_name"].tolist() == ["goals", "cards", "fouls", "shots"]
    assert not outputs["title_probability_summary"].empty
    assert outputs["top_scorer_forecast"].empty


def test_resolve_team_label_accepts_round_placeholders_with_case_and_plural_variants() -> None:
    winner_slots = {
        "round of 32 1 winner": "Brazil",
        "quarterfinal 1 winner": "France",
        "semifinal 1 winner": "Argentina",
    }
    loser_slots = {
        "semifinal 1 loser": "Spain",
    }

    assert _resolve_team_label(
        label="Round of 32 1 Winner",
        standings_by_group={},
        ranked_third_places=[],
        used_third_place_groups=set(),
        winner_slots=winner_slots,
        loser_slots=loser_slots,
    ) == "Brazil"
    assert _resolve_team_label(
        label="Quarterfinals 1 Winner",
        standings_by_group={},
        ranked_third_places=[],
        used_third_place_groups=set(),
        winner_slots=winner_slots,
        loser_slots=loser_slots,
    ) == "France"
    assert _resolve_team_label(
        label="Semifinals 1 Loser",
        standings_by_group={},
        ranked_third_places=[],
        used_third_place_groups=set(),
        winner_slots=winner_slots,
        loser_slots=loser_slots,
    ) == "Spain"


def test_build_real_serving_snapshot_blends_api_football_player_priors() -> None:
    class StubObservedClient:
        def fetch_completed_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-11":
                return [
                    {
                        "match_id": "501",
                        "match_date": "2026-06-11",
                        "stage": "Group A",
                        "home_team": "Brazil",
                        "away_team": "Mexico",
                        "home_goals": 2,
                        "away_goals": 1,
                        "home_shots": 12,
                        "away_shots": 8,
                        "status": "Final",
                        "source": "espn",
                        "source_retrieved_at": "2026-06-20T00:00:00Z",
                    }
                ]
            return []

    class StubScheduleClient:
        def fetch_matches_for_date(self, match_date: object) -> list[dict]:
            if str(match_date) == "2026-06-12":
                return [
                    {
                        "match_id": "502",
                        "match_date": "2026-06-12",
                        "stage": "Group A",
                        "home_team": "Brazil",
                        "away_team": "Canada",
                        "status": "Scheduled",
                        "source": "fifa",
                    }
                ]
            return []

    class StubAPIFootballClient:
        def search_team(self, team_name: str) -> dict | None:
            lookup = {
                "Brazil": {"id": 1, "name": "Brazil"},
                "Mexico": {"id": 2, "name": "Mexico"},
                "Canada": {"id": 3, "name": "Canada"},
            }
            return lookup.get(team_name)

        def fetch_team_recent_player_stats(self, team_id: int, season: int, team_name: str | None = None) -> list[dict]:
            rows = {
                1: [
                    {
                        "team": team_name,
                        "player_id": "9",
                        "player_name": "Atacante Brasil",
                        "position": "Forward",
                        "appearances": 18.0,
                        "sub_ins": 3.0,
                        "minutes": 1400.0,
                        "total_goals": 11.0,
                        "total_shots": 36.0,
                        "shots_on_target": 17.0,
                        "goal_assists": 4.0,
                        "yellow_cards": 2.0,
                        "red_cards": 0.0,
                        "fouls_committed": 10.0,
                        "fouls_suffered": 18.0,
                        "source": "api-football",
                    }
                ],
                2: [
                    {
                        "team": team_name,
                        "player_id": "10",
                        "player_name": "Atacante Mexico",
                        "position": "Forward",
                        "appearances": 16.0,
                        "sub_ins": 2.0,
                        "minutes": 1200.0,
                        "total_goals": 6.0,
                        "total_shots": 21.0,
                        "shots_on_target": 8.0,
                        "goal_assists": 1.0,
                        "yellow_cards": 3.0,
                        "red_cards": 0.0,
                        "fouls_committed": 9.0,
                        "fouls_suffered": 9.0,
                        "source": "api-football",
                    }
                ],
                3: [
                    {
                        "team": team_name,
                        "player_id": "11",
                        "player_name": "Atacante Canada",
                        "position": "Forward",
                        "appearances": 14.0,
                        "sub_ins": 5.0,
                        "minutes": 990.0,
                        "total_goals": 4.0,
                        "total_shots": 18.0,
                        "shots_on_target": 7.0,
                        "goal_assists": 2.0,
                        "yellow_cards": 1.0,
                        "red_cards": 0.0,
                        "fouls_committed": 8.0,
                        "fouls_suffered": 12.0,
                        "source": "api-football",
                    }
                ],
            }
            return rows.get(team_id, [])

    serving_dir = _make_temp_dir() / "serving"
    outputs = build_real_serving_snapshot(
        start_date="2026-06-11",
        end_date="2026-06-12",
        output_dir=serving_dir,
        client=StubObservedClient(),
        schedule_client=StubScheduleClient(),
        api_football_client=StubAPIFootballClient(),
    )

    assert not outputs["top_scorer_forecast"].empty
    assert outputs["top_scorer_forecast"]["player_name"].tolist()[0] == "Atacante Brasil"
    predicted_brazil = outputs["predictions"].loc[outputs["predictions"]["match_id"] == "502"]
    assert predicted_brazil["predicted_home_shots"].iloc[0] > 0.0
    assert predicted_brazil["predicted_home_fouls"].iloc[0] > 0.0
