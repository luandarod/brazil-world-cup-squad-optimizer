# World Cup Forecasting Lab Methodology

## Evaluation framework

The lab uses a simple layered evaluation setup:

- FIFA is the official truth layer for match outcomes, tournament progression, and final score references.
- Market odds are transformed into a market baseline so model quality is judged against an external expectation, not only against naive averages.
- Event models for goals, cards, and shots are trained and reviewed separately, which keeps target definitions clear and makes error analysis easier to interpret.
- Backtests in `src/evaluation/` produce comparable metrics and leaderboard artifacts before anything is surfaced in the app.

## Project structure

The repository is organized around the forecasting pipeline:

- `src/ingestion/` and `src/pipelines/` collect and normalize FIFA and market data.
- `src/features/` builds match-level predictors.
- `src/models/` contains target-specific forecasting logic and baseline helpers.
- `src/evaluation/` measures predictive quality and writes leaderboard outputs.
- `src/serving/` and `app/` package those outputs for interactive consumption.

This structure keeps source acquisition, feature generation, modeling, evaluation, and presentation loosely coupled so the lab can evolve each stage independently.
