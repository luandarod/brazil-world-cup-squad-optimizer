# World Cup Forecasting Lab

World Cup Forecasting Lab is a football analytics sandbox for estimating match-level World Cup outcomes, comparing modeling strategies, and packaging the results for interactive exploration.

The public Streamlit app is intentionally anchored to observed reality first. It exposes completed-match truth, forecast outputs, and tournament summaries only through explicit serving artifacts, so missing validation shows up as missing coverage instead of being hidden behind placeholder numbers.

The current repo focuses on a transparent forecasting stack:

- a FIFA official truth layer for final match results and tournament records;
- a market baseline built from bookmaker-style probabilities and price signals;
- event models for goals, cards, and shots;
- optional API-Football player-history priors for richer player and team context;
- evaluation outputs that compare learned models against simple baselines before publishing artifacts to the app;
- player-context-aware forecast serving for match, group, and knockout views.

## What this lab is trying to answer

The project asks a broader question than squad optimization:

> How much forecasting signal can we recover from public tournament data, FIFA truth data, and market expectations when predicting World Cup matches?

Instead of selecting a single Brazil lineup, the lab treats the tournament as a repeatable modeling problem with measurable targets and backtests.

## Repo map

```text
brazil-world-cup-squad-optimizer/
|-- app/
|   `-- streamlit_app.py
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- reference/
|-- reports/
|   |-- executive_summary.md
|   `-- methodology/
|       `-- world-cup-forecasting-lab.md
|-- src/
|   |-- evaluation/
|   |-- features/
|   |-- ingestion/
|   |-- models/
|   |-- pipelines/
|   `-- serving/
|-- tests/
`-- README.md
```

## Workflow

1. Ingest FIFA and market source data through the pipelines in `src/ingestion/` and `src/pipelines/`.
2. Build team and match features in `src/features/`.
3. Train or score target-specific models in `src/models/`.
4. Run backtests and summary metrics from `src/evaluation/`.
5. Export leaderboard and serving artifacts for the Streamlit interface.

## Evaluation stance

Every modeling pass is judged against a baseline, not in isolation.

- FIFA data acts as the official source of truth for outcomes.
- Market prices provide the market baseline the models must beat or at least explain.
- Goals, cards, and shots are evaluated as separate targets so the lab can measure calibration and error per event family.

## Public app contract

- `data/serving/observed_match_results.csv` is the public truth table for completed matches only.
- `data/serving/coverage_summary.csv` explains how much real observed coverage exists for each published target.
- `data/serving/match_predictions.csv` stores match-level forecast rows for completed and future fixtures.
- `data/serving/match_prediction_vs_actual.csv` stores scored comparisons for matches that already happened.
- `data/serving/group_forecast_summary.csv` stores projected group-stage standing context.
- `data/serving/knockout_forecast_summary.csv` stores projected knockout-path context.
- `data/serving/team_forecast_summary.csv` stores tournament outlook summaries by team.
- `data/serving/methodology_status.csv` stores publishability and truth-coverage status by target.
- `data/serving/title_probability_summary.csv` stores championship-probability ranking by team.
- `data/serving/top_scorer_forecast.csv` stores projected golden-boot style outputs by player.
- `src/pipelines/build_real_serving_snapshot.py` prefers FIFA when usable and falls back to the public ESPN scoreboard feed to keep the app populated with real observed matches.
- The app does not invent truth for unplayed matches or unavailable metrics.
- If a leaderboard, forecast comparison, or team view lacks real observed match truth, the app shows an explicit coverage message instead of a generic file-missing notice.

## Public serving outputs

- `observed_match_results.csv`: completed-match truth with source provenance, coverage, and lineup-context fields.
- `match_predictions.csv`: match-level forecast outputs for played and future matches.
- `match_prediction_vs_actual.csv`: forecast-versus-truth comparisons for already played matches.
- `group_forecast_summary.csv`: projected group standings, points, and remaining-match context.
- `knockout_forecast_summary.csv`: projected knockout-stage paths derived from future fixtures.
- `team_forecast_summary.csv`: observed plus projected team outlook at tournament level.
- `methodology_status.csv`: target-by-target publication state for goals, shots, cards, and fouls.
- `title_probability_summary.csv`: title-probability outlook derived from team priors plus projected path.
- `top_scorer_forecast.csv`: player-level projected scoring table built from public roster context.

## Observed vs Probable Context

Completed matches can use observed lineup and substitution context where a source provides it. Future fixtures use probable lineup aggregates, so the app can discuss expected squad shape without pretending that pre-match context is observed truth.

See `reports/methodology/world-cup-forecasting-lab.md` for the concise methodology note behind this structure.

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest tests -v
streamlit run app/streamlit_app.py
```

For local-only enrichment secrets, prefer `.env.local` instead of committing anything into the repo:

```bash
copy .env.example .env.local
```

Then set:

```bash
API_FOOTBALL_KEY=your_local_key
API_FOOTBALL_HOST=v3.football.api-sports.io
API_FOOTBALL_PRIOR_SEASON=2025
```

To refresh the public snapshot with currently completed World Cup 2026 matches and regenerate forecast artifacts:

```bash
python -m src.pipelines.build_real_serving_snapshot --start-date 2026-06-11 --end-date 2026-06-15 --disable-ssl-verification
```

## Stable deployment

The repo now includes deploy-ready Streamlit and container assets:

- `.streamlit/config.toml` for headless public app defaults;
- `Dockerfile` for containerized hosting;
- `render.yaml` for a one-service Render deployment on a paid always-on instance.

For a stable public deployment on Render:

1. Push the repo with the latest `data/serving/` artifacts committed.
2. Create a new Render Blueprint or Web Service from this repository.
3. Render will detect `render.yaml` and build the app from `Dockerfile`.
4. The blueprint is configured for the `starter` instance type so the service stays awake and exposes a permanent `onrender.com` URL.
5. If you only need a temporary test deployment, you can manually switch the service to `free`, but free Render web services spin down after 15 minutes of inactivity.
6. Set any local-only secrets, such as `API_FOOTBALL_KEY`, only in the platform environment settings if you want player-prior enrichment during future rebuilds.
7. After deploy, validate:
   - `/` loads the Streamlit app
   - `Panorama`, `Grupos`, and `Caminho do Mata-mata` render cards instead of raw HTML
   - `data/serving/top_scorer_forecast.csv` and `title_probability_summary.csv` are reflected in the live UI
