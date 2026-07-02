from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import has_api_football_credentials
from src.ingestion.api_football_client import APIFootballClient
from src.ingestion.espn_client import ESPNClient
from src.ingestion.espn_roster_client import ESPNRosterClient
from src.ingestion.lineup_client import LineupClient
from src.features.team_match_features import build_team_match_features
from src.evaluation.run_backtest import run_backtest
from src.serving.load_outputs import write_serving_outputs
from src.data_cleaning import clean_player_stats
from src.feature_engineering import add_features
from src.scoring_model import calculate_scores
from src.tournament_predictor import calculate_composite_strength

from src.pipelines.ingest_sources import (
    _load_normalized_matches,
    _load_future_fixtures,
    _build_public_match_frame,
    _attach_player_context,
    _rows_have_team_ids,
    PUBLIC_MATCH_COLUMNS,
    TOURNAMENT_FINAL_DATE,
)

from src.pipelines.process_features import (
    _build_team_priors,
    _build_team_match_history,
    _build_target_feature_table,
    TOP_SCORER_COLUMNS,
)

from src.pipelines.run_simulations import (
    _merge_prediction_context,
    _build_future_side_predictions,
    _combine_side_predictions,
    _build_public_match_predictions,
    _combine_match_predictions,
    _build_future_match_predictions,
    _build_prediction_vs_actual,
    _build_group_forecast_summary,
    _build_knockout_forecast_summary,
    _build_team_forecast_summary,
    _build_title_probability_summary,
    _build_top_scorer_forecast,
    _build_methodology_status,
    _build_coverage_summary,
    _build_team_summary,
    LEADERBOARD_COLUMNS,
    PREDICTION_COLUMNS,
    MATCH_COMPARISON_COLUMNS,
    GROUP_FORECAST_COLUMNS,
    KNOCKOUT_FORECAST_COLUMNS,
    TEAM_FORECAST_COLUMNS,
    METHODOLOGY_STATUS_COLUMNS,
    TITLE_PROBABILITY_COLUMNS,
    TEAM_SUMMARY_COLUMNS,
)


def build_real_serving_snapshot(
    start_date: str,
    end_date: str,
    output_dir: Path,
    client: ESPNClient | None = None,
    schedule_client: object | None = None,
    lineup_client: LineupClient | None = None,
    roster_client: ESPNRosterClient | None = None,
    api_football_client: APIFootballClient | None = None,
    disable_ssl_verification: bool = False,
    forecast_end_date: str | None = None,
) -> dict[str, pd.DataFrame]:
    normalized_matches = _load_normalized_matches(
        start_date=start_date,
        end_date=end_date,
        client=client,
        disable_ssl_verification=disable_ssl_verification,
    )
    if schedule_client is None:
        schedule_client = ESPNClient(verify_ssl=not disable_ssl_verification)
    future_fixture_rows = _load_future_fixtures(
        start_date=start_date,
        end_date=forecast_end_date or TOURNAMENT_FINAL_DATE,
        schedule_client=schedule_client,
    )

    observed_results = _build_public_match_frame(normalized_matches, is_future_fixture=False)
    future_fixtures = _build_public_match_frame(future_fixture_rows, is_future_fixture=True)
    if lineup_client is not None:
        observed_results = _attach_player_context(observed_results, lineup_client)
        future_fixtures = _attach_player_context(future_fixtures, lineup_client)
    coverage = _build_coverage_summary(observed_results)
    teams = _build_team_summary(observed_results)
    if roster_client is None and _rows_have_team_ids(normalized_matches + future_fixture_rows):
        roster_client = ESPNRosterClient(verify_ssl=not disable_ssl_verification)
    if api_football_client is None and has_api_football_credentials():
        api_football_client = APIFootballClient()
    team_priors, roster_players = _build_team_priors(
        match_rows=normalized_matches + future_fixture_rows,
        observed_results=observed_results,
        future_fixtures=future_fixtures,
        roster_client=roster_client,
        api_football_client=api_football_client,
    )
    team_match_history = _build_team_match_history(observed_results, future_fixtures, team_priors)
    featured_history = build_team_match_features(team_match_history)
    observed_feature_table = _build_target_feature_table(
        featured_history.loc[~featured_history["is_future_fixture"]].copy()
    )
    backtest_outputs = run_backtest(observed_feature_table)
    observed_side_predictions = _merge_prediction_context(
        backtest_outputs["predictions"],
        observed_feature_table,
    )
    observed_predictions = _build_public_match_predictions(observed_side_predictions)
    future_predictions = _build_future_match_predictions(
        future_fixtures=future_fixtures,
        observed_results=observed_results,
        team_priors=team_priors,
    )
    predictions = _combine_match_predictions(
        observed_predictions,
        future_predictions,
    )
    match_prediction_vs_actual = _build_prediction_vs_actual(predictions, observed_results)
    group_forecast_summary = _build_group_forecast_summary(
        predictions,
        observed_results,
    )
    knockout_forecast_summary = _build_knockout_forecast_summary(predictions)
    team_forecast_summary = _build_team_forecast_summary(teams, predictions)
    title_probability_summary = _build_title_probability_summary(
        team_priors=team_priors,
        team_forecast_summary=team_forecast_summary,
        knockout_forecast_summary=knockout_forecast_summary,
    )
    top_scorer_forecast = _build_top_scorer_forecast(
        roster_players=roster_players,
        team_forecast_summary=team_forecast_summary,
    )
    methodology_status = _build_methodology_status(coverage, predictions)

    try:
        players_path = Path("data/processed/sample_brazil_players.csv")
        if players_path.exists():
            df_players = pd.read_csv(players_path)
            df_cleaned = clean_player_stats(df_players)
            df_featured = add_features(df_cleaned)
            df_scored = calculate_scores(df_featured)
            
            from src.squad_optimizer import assign_squad_role, select_best_xi, select_reserves
            df_assigned = assign_squad_role(df_scored)
            xi = select_best_xi(df_assigned)
            reserves = select_reserves(df_assigned, xi)
            
            xi = xi.copy()
            reserves = reserves.copy()
            xi["squad_role"] = "XI"
            reserves["squad_role"] = "Reserve"
            
            squad_optimizer_results = pd.concat([xi, reserves], ignore_index=True)
        else:
            squad_optimizer_results = pd.DataFrame()
    except Exception:
        squad_optimizer_results = pd.DataFrame()

    write_serving_outputs(
        output_dir,
        leaderboard=backtest_outputs["leaderboard"],
        predictions=predictions,
        teams=teams,
        coverage_summary=coverage,
        observed_match_results=observed_results,
        match_prediction_vs_actual=match_prediction_vs_actual,
        group_forecast_summary=group_forecast_summary,
        knockout_forecast_summary=knockout_forecast_summary,
        team_forecast_summary=team_forecast_summary,
        methodology_status=methodology_status,
        title_probability_summary=title_probability_summary,
        top_scorer_forecast=top_scorer_forecast,
        squad_optimizer_results=squad_optimizer_results,
    )
    return {
        "observed_results": observed_results,
        "future_fixtures": future_fixtures,
        "coverage": coverage,
        "teams": teams,
        "leaderboard": backtest_outputs["leaderboard"],
        "predictions": predictions,
        "match_prediction_vs_actual": match_prediction_vs_actual,
        "group_forecast_summary": group_forecast_summary,
        "knockout_forecast_summary": knockout_forecast_summary,
        "team_forecast_summary": team_forecast_summary,
        "methodology_status": methodology_status,
        "title_probability_summary": title_probability_summary,
        "top_scorer_forecast": top_scorer_forecast,
        "squad_optimizer_results": squad_optimizer_results,
    }



def main() -> None:
    parser = argparse.ArgumentParser(description="Build real serving snapshot artifacts from ESPN scoreboard data.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--forecast-end-date", default=TOURNAMENT_FINAL_DATE)
    parser.add_argument("--output-dir", default=str(Path("data/serving")))
    parser.add_argument("--disable-ssl-verification", action="store_true")
    args = parser.parse_args()

    build_real_serving_snapshot(
        start_date=args.start_date,
        end_date=args.end_date,
        forecast_end_date=args.forecast_end_date,
        output_dir=Path(args.output_dir),
        disable_ssl_verification=args.disable_ssl_verification,
    )



if __name__ == "__main__":
    main()
