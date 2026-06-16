# World Cup Forecasting Lab

World Cup Forecasting Lab is a football analytics sandbox for estimating match-level World Cup outcomes, comparing modeling strategies, and packaging the results for interactive exploration.

The public Streamlit app is intentionally real-data-only. It only exposes outputs backed by observed match truth and explicit coverage artifacts, so missing validation is shown as missing coverage rather than hidden behind placeholder numbers.

The current repo focuses on a transparent forecasting stack:

- a FIFA official truth layer for final match results and tournament records;
- a market baseline built from bookmaker-style probabilities and price signals;
- event models for goals, cards, and shots;
- evaluation outputs that compare learned models against simple baselines before publishing artifacts to the app.

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
- The app does not invent truth for unplayed matches or unavailable metrics.
- If a leaderboard, forecast comparison, or team view lacks real observed match truth, the app shows an explicit coverage message instead of a generic file-missing notice.

See `reports/methodology/world-cup-forecasting-lab.md` for the concise methodology note behind this structure.

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest tests -v
streamlit run app/streamlit_app.py
```
