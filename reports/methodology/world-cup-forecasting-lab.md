# World Cup Forecasting Lab Methodology

## Evaluation framework

The lab uses a simple layered evaluation setup:

- FIFA is the official truth layer for match outcomes, tournament progression, and final score references.
- Market odds are transformed into a market baseline so model quality is judged against an external expectation, not only against naive averages.
- Event models for goals, cards, and shots are trained and reviewed separately, which keeps target definitions clear and makes error analysis easier to interpret.
- Backtests in `src/evaluation/` produce comparable metrics and leaderboard artifacts before anything is surfaced in the app.

## Real-data public contract

The public app is intentionally scoped to observed reality first, not simulated completeness.

- `observed_match_results.csv` contains only completed matches with real observed truth.
- `coverage_summary.csv` documents which targets have enough observed truth to support public evaluation.
- `match_predictions.csv` publishes match-level forecasts for completed and future fixtures.
- `match_prediction_vs_actual.csv` publishes scored forecast comparisons once a match has already been played.
- `group_forecast_summary.csv`, `knockout_forecast_summary.csv`, and `team_forecast_summary.csv` publish tournament-level rollups from the serving layer.
- `title_probability_summary.csv` and `top_scorer_forecast.csv` publish tournament-level title and player-scoring outlooks.
- `methodology_status.csv` keeps target-by-target publication status explicit.
- FIFA remains the primary truth source for match identity and final scores.
- When FIFA page extraction is unavailable in a local environment, the public serving snapshot can fall back to the ESPN World Cup scoreboard as a free public complementary source, with provenance kept explicit in the output rows.
- When non-score metrics are unavailable or only partially observed, the app keeps those gaps visible instead of manufacturing values or implying full coverage.
- Public-facing tabs may stay sparse until enough observed matches exist to support fair comparisons.

## Observed vs probable context

Completed matches can use observed lineup and substitution context where it is available in the public data source. Future fixtures use probable lineup aggregates so the tournament views can discuss likely squad structure without pretending that inferred pre-match context is already observed fact.

This split matters in the app:

- Match evaluation rows are judged against observed truth only.
- Future tournament scenarios can use probable lineup aggregates and still remain honest about what is inferred.
- Cards can stay forecast-only when the truth layer does not support them yet, even if the rest of the forecast stack is populated.

## Player priors layer

The current serving stack no longer relies only on tournament averages and team-level strength priors.

- ESPN public roster data is used as the first free player-context layer.
- API-Football can be enabled locally as an additional player-history source for recent appearances, goals, shots, cards, and fouls.
- The pipeline blends those player-history signals into team priors so projected goals, discipline, and top-scorer views reflect squad composition instead of only already-played World Cup matches.
- Source provenance stays explicit in the repo and app so richer player priors do not get confused with observed tournament truth.

## Project structure

The repository is organized around the forecasting pipeline:

- `src/ingestion/` and `src/pipelines/` collect and normalize FIFA and market data.
- `src/features/` builds match-level predictors, including probable lineup aggregates.
- `src/models/` contains target-specific forecasting logic and baseline helpers.
- `src/evaluation/` measures predictive quality and writes leaderboard outputs.
- `src/serving/` and `app/` package match forecasts, prediction-vs-actual comparisons, group scenarios, knockout paths, and methodology status for interactive consumption.

This structure keeps source acquisition, feature generation, modeling, evaluation, and presentation loosely coupled so the lab can evolve each stage independently.
