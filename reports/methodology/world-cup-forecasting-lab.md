# World Cup Forecasting Lab Methodology

## Evaluation framework

The lab uses a simple layered evaluation setup:

- FIFA is the official truth layer for match outcomes, tournament progression, and final score references.
- Market odds are transformed into a market baseline so model quality is judged against an external expectation, not only against naive averages.
- Event models for goals, cards, and shots are trained and reviewed separately, which keeps target definitions clear and makes error analysis easier to interpret.
- Backtests in `src/evaluation/` produce comparable metrics and leaderboard artifacts before anything is surfaced in the app.

## Real-data public contract

The public app is intentionally scoped to observed reality, not simulated completeness.

- `observed_match_results.csv` contains only completed matches with real observed truth.
- `coverage_summary.csv` documents which targets have enough observed truth to support public evaluation.
- FIFA remains the primary truth source for match identity and final scores.
- When FIFA page extraction is unavailable in a local environment, the public serving snapshot can fall back to the ESPN World Cup scoreboard as a free public complementary source, with provenance kept explicit in the output rows.
- When non-score metrics are unavailable or only partially observed, the app keeps those gaps visible instead of manufacturing values or implying full coverage.
- Public-facing tabs may stay sparse until enough observed matches exist to support fair comparisons.

## Project structure

The repository is organized around the forecasting pipeline:

- `src/ingestion/` and `src/pipelines/` collect and normalize FIFA and market data.
- `src/features/` builds match-level predictors.
- `src/models/` contains target-specific forecasting logic and baseline helpers.
- `src/evaluation/` measures predictive quality and writes leaderboard outputs.
- `src/serving/` and `app/` package those outputs for interactive consumption.

This structure keeps source acquisition, feature generation, modeling, evaluation, and presentation loosely coupled so the lab can evolve each stage independently.
