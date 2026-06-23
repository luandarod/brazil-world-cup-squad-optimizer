# World Cup Event Forecasting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current real-data World Cup app into a publishable event-first forecasting platform with non-empty model outputs, observed-vs-predicted comparisons, group and knockout projections, and player-context-aware match intelligence.

**Architecture:** Keep the current observed truth layer as the base, enrich it with player-context and future-fixture context, build deterministic team and player aggregate features, generate target-specific model forecasts through a temporal backtest pipeline, then publish expanded serving artifacts that the Streamlit app can expose honestly across played and future matches.

**Tech Stack:** Python, pandas, pydantic, pytest, Streamlit

---

## File Structure

- Create: `src/ingestion/lineup_client.py`
  Responsibility: normalize public lineup, bench, and substitution context for observed and future matches.
- Modify: `src/domain/match_schema.py`
  Responsibility: define stable public contracts for enriched truth rows, forecast rows, and match comparison rows.
- Modify: `src/pipelines/build_real_serving_snapshot.py`
  Responsibility: ingest observed matches plus future fixtures and return schedule-aware, player-context-aware snapshot inputs.
- Modify: `tests/test_match_schema.py`
  Responsibility: lock new schema behavior and forbid silent contract drift.
- Modify: `tests/test_real_serving_snapshot.py`
  Responsibility: verify enriched snapshot outputs and future-fixture handling.
- Create: `src/features/player_context_features.py`
  Responsibility: convert confirmed and probable player context into aggregate team features.
- Modify: `src/features/team_match_features.py`
  Responsibility: combine existing recent-form features with lineup stability, bench depth, and schedule context.
- Modify: `tests/test_team_match_features.py`
  Responsibility: lock deterministic feature engineering for team and player context.
- Modify: `src/models/baselines.py`
  Responsibility: implement sports-relevant deterministic baselines for goals, shots, and cards.
- Modify: `src/models/goals.py`
  Responsibility: fit and score goal forecasts from feature tables.
- Modify: `src/models/shots.py`
  Responsibility: fit and score shot forecasts from feature tables.
- Modify: `src/models/cards.py`
  Responsibility: gate card forecasts behind coverage and return empty outputs safely when unavailable.
- Modify: `src/evaluation/run_backtest.py`
  Responsibility: execute temporal train-score-evaluate loops and emit match-level predictions plus leaderboard rows.
- Modify: `src/evaluation/metrics.py`
  Responsibility: score model outputs by target and surface target-specific metrics for public display.
- Create: `tests/test_run_backtest.py`
  Responsibility: lock the temporal evaluation contract and prevent leakage.
- Modify: `tests/test_evaluation_metrics.py`
  Responsibility: lock expanded leaderboard metrics and target grouping behavior.
- Modify: `src/serving/load_outputs.py`
  Responsibility: write and read expanded serving artifacts for forecasts, comparisons, groups, knockout, and methodology status.
- Modify: `tests/test_serving_outputs.py`
  Responsibility: lock the expanded serving CSV contract.
- Modify: `app/streamlit_app.py`
  Responsibility: render non-empty forecasting, observed-vs-predicted comparisons, and tournament projection views.
- Modify: `tests/test_streamlit_contract.py`
  Responsibility: lock the public app wording and navigation for the new analytical surface.
- Modify: `README.md`
  Responsibility: explain the new forecasting flow, output artifacts, and honesty contract.
- Modify: `reports/methodology/world-cup-forecasting-lab.md`
  Responsibility: document observed versus probable context, temporal evaluation, and target coverage.

### Task 1: Enrich the truth layer with player context and future fixtures

**Files:**
- Create: `src/ingestion/lineup_client.py`
- Modify: `src/domain/match_schema.py`
- Modify: `src/pipelines/build_real_serving_snapshot.py`
- Modify: `tests/test_match_schema.py`
- Modify: `tests/test_real_serving_snapshot.py`

- [ ] **Step 1: Write the failing schema and snapshot tests**

```python
def test_public_match_truth_row_supports_player_context_fields() -> None:
    row = PublicMatchTruthRow(
        match_id="760419",
        match_date="2026-06-13",
        stage="Group C",
        home_team="Brazil",
        away_team="Morocco",
        home_goals=1,
        away_goals=1,
        home_shots=12,
        away_shots=14,
        home_cards=None,
        away_cards=None,
        status="Full Time",
        source="espn",
        is_future_fixture=False,
        home_lineup_confirmed=True,
        away_lineup_confirmed=True,
        home_probable_lineup_count=11,
        away_probable_lineup_count=11,
        home_substitutions_used=5,
        away_substitutions_used=4,
    )

    assert row.model_dump()["home_substitutions_used"] == 5
```

```python
def test_build_real_serving_snapshot_publishes_observed_and_future_match_inputs() -> None:
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
                        "is_future_fixture": True,
                    }
                ]
            return []

    class StubObservedClient:
        def fetch_completed_matches_for_date(self, match_date: object) -> list[dict]:
            return []

    outputs = build_real_serving_snapshot(
        start_date="2026-06-16",
        end_date="2026-06-16",
        output_dir=serving_dir,
        client=StubObservedClient(),
        schedule_client=StubScheduleClient(),
    )

    assert outputs["future_fixtures"].to_dict("records") == [
        {
            "match_id": "760430",
            "match_date": "2026-06-16",
            "stage": "Group F",
            "home_team": "Japan",
            "away_team": "Nigeria",
            "status": "Scheduled",
            "is_future_fixture": True,
        }
    ]
```

- [ ] **Step 2: Run the focused truth-layer tests and verify they fail**

Run: `pytest tests/test_match_schema.py tests/test_real_serving_snapshot.py -v`
Expected: FAIL because the schemas and snapshot builder do not yet expose player-context fields or future fixtures.

- [ ] **Step 3: Implement the minimal enriched truth and schedule contract**

```python
class PublicMatchTruthRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    match_date: str
    stage: str
    home_team: str
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_cards: int | None = None
    away_cards: int | None = None
    status: str
    source: str
    is_future_fixture: bool = False
    home_lineup_confirmed: bool = False
    away_lineup_confirmed: bool = False
    home_probable_lineup_count: int = 0
    away_probable_lineup_count: int = 0
    home_substitutions_used: int = 0
    away_substitutions_used: int = 0
```

```python
class LineupClient:
    def fetch_match_player_context(self, match_id: str) -> dict:
        return {
            "home_lineup_confirmed": False,
            "away_lineup_confirmed": False,
            "home_probable_lineup_count": 0,
            "away_probable_lineup_count": 0,
            "home_substitutions_used": 0,
            "away_substitutions_used": 0,
        }
```

```python
def build_real_serving_snapshot(..., schedule_client: object | None = None, lineup_client: LineupClient | None = None) -> dict[str, pd.DataFrame]:
    observed_results = pd.DataFrame(_load_normalized_matches(...), columns=OBSERVED_RESULT_COLUMNS)
    future_fixtures = pd.DataFrame(_load_future_fixtures(...), columns=FUTURE_FIXTURE_COLUMNS)

    if lineup_client is not None and not observed_results.empty:
        observed_results = _attach_player_context(observed_results, lineup_client)
    if lineup_client is not None and not future_fixtures.empty:
        future_fixtures = _attach_player_context(future_fixtures, lineup_client)

    ...
    return {
        "observed_results": observed_results,
        "future_fixtures": future_fixtures,
        "coverage": coverage,
        "teams": teams,
    }
```

- [ ] **Step 4: Re-run the focused truth-layer tests**

Run: `pytest tests/test_match_schema.py tests/test_real_serving_snapshot.py -v`
Expected: PASS

- [ ] **Step 5: Commit the enriched truth-layer slice**

```bash
git add src/ingestion/lineup_client.py src/domain/match_schema.py src/pipelines/build_real_serving_snapshot.py tests/test_match_schema.py tests/test_real_serving_snapshot.py
git commit -m "feat: add player-context tournament snapshot"
```

### Task 2: Build deterministic team and player-context features

**Files:**
- Create: `src/features/player_context_features.py`
- Modify: `src/features/team_match_features.py`
- Modify: `tests/test_team_match_features.py`

- [ ] **Step 1: Write the failing feature tests**

```python
def test_build_player_context_features_aggregates_lineup_and_bench_signals() -> None:
    matches = pd.DataFrame(
        [
            {
                "match_id": "760419",
                "team": "Brazil",
                "match_date": "2026-06-13",
                "home_lineup_confirmed": True,
                "home_probable_lineup_count": 11,
                "home_substitutions_used": 5,
                "home_player_minutes_proxy": 990,
            }
        ]
    )

    featured = build_player_context_features(matches, team_column="team")

    assert featured.loc[0, "lineup_confirmed_flag"] == 1.0
    assert featured.loc[0, "probable_lineup_completeness"] == 1.0
    assert featured.loc[0, "bench_usage_rate"] == 5 / 5
```

```python
def test_build_team_match_features_merges_recent_form_and_player_context() -> None:
    matches = pd.DataFrame(
        [
            {
                "match_id": "bra-1",
                "match_date": "2026-06-01",
                "team": "Brazil",
                "goals_for": 1,
                "cards_for": 2,
                "shots_for": 3,
                "lineup_confirmed_flag": 1.0,
                "probable_lineup_completeness": 1.0,
            }
        ]
    )

    featured = build_team_match_features(matches)

    assert "lineup_confirmed_flag" in featured.columns
    assert "team_goals_avg_last_3" in featured.columns
```

- [ ] **Step 2: Run the feature test file and verify it fails**

Run: `pytest tests/test_team_match_features.py -v`
Expected: FAIL because the project does not yet aggregate player context into feature columns.

- [ ] **Step 3: Implement the player-context feature builder and merge it into the existing feature layer**

```python
def build_player_context_features(matches: pd.DataFrame, team_column: str = "team") -> pd.DataFrame:
    featured = matches.copy()
    featured["lineup_confirmed_flag"] = featured.get("lineup_confirmed_flag", featured.get("home_lineup_confirmed", False)).astype(float)
    featured["probable_lineup_completeness"] = (
        featured.get("probable_lineup_count", featured.get("home_probable_lineup_count", 0)).fillna(0).astype(float) / 11.0
    ).clip(lower=0.0, upper=1.0)
    featured["bench_usage_rate"] = (
        featured.get("substitutions_used", featured.get("home_substitutions_used", 0)).fillna(0).astype(float) / 5.0
    ).clip(lower=0.0, upper=1.0)
    return featured
```

```python
def build_team_match_features(matches: pd.DataFrame) -> pd.DataFrame:
    featured = build_player_context_features(matches)
    ...
    passthrough_columns = [
        "lineup_confirmed_flag",
        "probable_lineup_completeness",
        "bench_usage_rate",
    ]
    return featured.sort_values("_original_row_order").reset_index(drop=True)
```

- [ ] **Step 4: Re-run the feature tests**

Run: `pytest tests/test_team_match_features.py -v`
Expected: PASS

- [ ] **Step 5: Commit the feature-engineering slice**

```bash
git add src/features/player_context_features.py src/features/team_match_features.py tests/test_team_match_features.py
git commit -m "feat: add player-context forecasting features"
```

### Task 3: Implement temporal backtests and event-target model outputs

**Files:**
- Modify: `src/models/baselines.py`
- Modify: `src/models/goals.py`
- Modify: `src/models/shots.py`
- Modify: `src/models/cards.py`
- Modify: `src/evaluation/run_backtest.py`
- Modify: `src/evaluation/metrics.py`
- Create: `tests/test_run_backtest.py`
- Modify: `tests/test_evaluation_metrics.py`

- [ ] **Step 1: Write the failing backtest and metrics tests**

```python
def test_run_backtest_returns_match_level_predictions_and_leaderboard() -> None:
    feature_table = pd.DataFrame(
        [
            {"match_id": "m1", "match_date": "2026-06-11", "team": "Brazil", "target_name": "goals_for", "actual_value": 2, "team_goals_avg_last_3": 1.4},
            {"match_id": "m2", "match_date": "2026-06-13", "team": "Brazil", "target_name": "goals_for", "actual_value": 1, "team_goals_avg_last_3": 1.8},
        ]
    )

    outputs = run_backtest(feature_table)

    assert set(outputs.keys()) == {"predictions", "leaderboard"}
    assert list(outputs["predictions"].columns)[:4] == ["match_id", "team", "model_name", "target_name"]
    assert "mae" in outputs["leaderboard"].columns
```

```python
def test_score_predictions_keeps_target_level_metrics_separate() -> None:
    predictions = pd.DataFrame(
        [
            {"model_name": "moving-average", "target_name": "goals_for", "predicted_value": 1.5, "actual_value": 2.0},
            {"model_name": "moving-average", "target_name": "shots_for", "predicted_value": 9.0, "actual_value": 8.0},
        ]
    )

    scored = score_predictions(predictions)

    assert scored["target_name"].tolist() == ["goals_for", "shots_for"]
```

- [ ] **Step 2: Run the evaluation tests and verify they fail**

Run: `pytest tests/test_run_backtest.py tests/test_evaluation_metrics.py -v`
Expected: FAIL because `run_backtest` still returns only a grouped score frame and no target-specific model outputs.

- [ ] **Step 3: Implement sports baselines and a minimal temporal backtest contract**

```python
@dataclass(frozen=True)
class BaselineModelSpec:
    model_name: str
    target_name: str
    feature_column: str


def default_baseline_specs() -> list[BaselineModelSpec]:
    return [
        BaselineModelSpec("moving-average", "goals_for", "team_goals_avg_last_3"),
        BaselineModelSpec("moving-average", "shots_for", "team_shots_avg_last_3"),
        BaselineModelSpec("moving-average", "cards_for", "team_cards_avg_last_3"),
    ]
```

```python
def run_backtest(feature_table: pd.DataFrame) -> dict[str, pd.DataFrame]:
    scored_rows: list[dict] = []
    for spec in default_baseline_specs():
        target_rows = feature_table.loc[feature_table["target_name"] == spec.target_name].copy()
        if target_rows.empty:
            continue
        target_rows["model_name"] = spec.model_name
        target_rows["predicted_value"] = target_rows[spec.feature_column].astype(float)
        scored_rows.extend(target_rows[["match_id", "team", "model_name", "target_name", "predicted_value", "actual_value"]].to_dict("records"))

    predictions = pd.DataFrame(scored_rows)
    leaderboard = score_predictions(predictions) if not predictions.empty else pd.DataFrame(columns=["model_name", "target_name", "exact_hit_rate", "mae", "rmse", "bias"])
    return {"predictions": predictions, "leaderboard": leaderboard}
```

```python
def score_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    ...
    summary["observations"] = scored.groupby(["model_name", "target_name"])["actual_value"].size().to_numpy()
    return summary[["model_name", "target_name", "observations", "exact_hit_rate", "mae", "rmse", "bias"]]
```

- [ ] **Step 4: Add goal, shots, and card model wrappers that degrade safely**

```python
def score_goal_models(feature_table: pd.DataFrame) -> pd.DataFrame:
    return _score_target_family(feature_table, target_name="goals_for", fallback_column="team_goals_avg_last_3")


def score_shot_models(feature_table: pd.DataFrame) -> pd.DataFrame:
    return _score_target_family(feature_table, target_name="shots_for", fallback_column="team_shots_avg_last_3")


def score_card_models(feature_table: pd.DataFrame) -> pd.DataFrame:
    if "has_cards_truth" in feature_table.columns and not feature_table["has_cards_truth"].any():
        return pd.DataFrame(columns=["match_id", "team", "model_name", "target_name", "predicted_value", "actual_value"])
    return _score_target_family(feature_table, target_name="cards_for", fallback_column="team_cards_avg_last_3")
```

- [ ] **Step 5: Re-run the evaluation tests**

Run: `pytest tests/test_run_backtest.py tests/test_evaluation_metrics.py -v`
Expected: PASS

- [ ] **Step 6: Commit the model-and-backtest slice**

```bash
git add src/models/baselines.py src/models/goals.py src/models/shots.py src/models/cards.py src/evaluation/run_backtest.py src/evaluation/metrics.py tests/test_run_backtest.py tests/test_evaluation_metrics.py
git commit -m "feat: add temporal event forecasting backtests"
```

### Task 4: Publish expanded serving artifacts for match, group, and knockout intelligence

**Files:**
- Modify: `src/serving/load_outputs.py`
- Modify: `src/pipelines/build_real_serving_snapshot.py`
- Modify: `tests/test_serving_outputs.py`
- Modify: `tests/test_real_serving_snapshot.py`

- [ ] **Step 1: Write the failing serving-output tests**

```python
def test_write_serving_outputs_creates_forecast_and_comparison_artifacts() -> None:
    write_serving_outputs(
        serving_dir,
        leaderboard=leaderboard,
        predictions=predictions,
        teams=teams,
        coverage_summary=coverage,
        observed_match_results=observed,
        match_prediction_vs_actual=comparisons,
        group_forecast_summary=groups,
        knockout_forecast_summary=knockout,
        team_forecast_summary=team_forecasts,
        methodology_status=methodology,
    )

    assert (serving_dir / "match_prediction_vs_actual.csv").exists()
    assert (serving_dir / "group_forecast_summary.csv").exists()
    assert (serving_dir / "knockout_forecast_summary.csv").exists()
```

```python
def test_build_real_serving_snapshot_writes_non_empty_forecast_artifacts_from_fixture_data() -> None:
    outputs = build_real_serving_snapshot(...)
    assert not read_match_predictions(serving_dir).empty
    assert not read_model_leaderboard(serving_dir).empty
```

- [ ] **Step 2: Run the serving tests and verify they fail**

Run: `pytest tests/test_serving_outputs.py tests/test_real_serving_snapshot.py -v`
Expected: FAIL because the serving layer only writes observed truth, coverage, and teams.

- [ ] **Step 3: Expand the writer and readers for the new public contract**

```python
def write_serving_outputs(
    base_dir: Path,
    leaderboard: pd.DataFrame,
    predictions: pd.DataFrame,
    teams: pd.DataFrame,
    coverage_summary: pd.DataFrame | None = None,
    observed_match_results: pd.DataFrame | None = None,
    match_prediction_vs_actual: pd.DataFrame | None = None,
    group_forecast_summary: pd.DataFrame | None = None,
    knockout_forecast_summary: pd.DataFrame | None = None,
    team_forecast_summary: pd.DataFrame | None = None,
    methodology_status: pd.DataFrame | None = None,
) -> None:
    ...
    optional_frames = {
        "coverage_summary.csv": coverage_summary,
        "observed_match_results.csv": observed_match_results,
        "match_prediction_vs_actual.csv": match_prediction_vs_actual,
        "group_forecast_summary.csv": group_forecast_summary,
        "knockout_forecast_summary.csv": knockout_forecast_summary,
        "team_forecast_summary.csv": team_forecast_summary,
        "methodology_status.csv": methodology_status,
    }
```

```python
def read_match_prediction_vs_actual(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "match_prediction_vs_actual.csv")


def read_group_forecast_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "group_forecast_summary.csv")
```

- [ ] **Step 4: Wire the snapshot pipeline to publish non-empty forecast rows**

```python
backtest_outputs = run_backtest(feature_table)
predictions = _build_public_match_predictions(backtest_outputs["predictions"], future_fixtures)
comparisons = _build_prediction_vs_actual(backtest_outputs["predictions"])
group_summary = _build_group_forecast_summary(predictions, observed_results)
knockout_summary = _build_knockout_forecast_summary(predictions, future_fixtures)
team_forecast_summary = _build_team_forecast_summary(teams, predictions)
methodology_status = _build_methodology_status(coverage, predictions)

write_serving_outputs(
    output_dir,
    leaderboard=backtest_outputs["leaderboard"],
    predictions=predictions,
    teams=teams,
    coverage_summary=coverage,
    observed_match_results=observed_results,
    match_prediction_vs_actual=comparisons,
    group_forecast_summary=group_summary,
    knockout_forecast_summary=knockout_summary,
    team_forecast_summary=team_forecast_summary,
    methodology_status=methodology_status,
)
```

- [ ] **Step 5: Re-run the serving tests**

Run: `pytest tests/test_serving_outputs.py tests/test_real_serving_snapshot.py -v`
Expected: PASS

- [ ] **Step 6: Commit the serving-artifact slice**

```bash
git add src/serving/load_outputs.py src/pipelines/build_real_serving_snapshot.py tests/test_serving_outputs.py tests/test_real_serving_snapshot.py
git commit -m "feat: publish tournament forecasting artifacts"
```

### Task 5: Remodel the public Streamlit app around non-empty forecasting and tournament intelligence

**Files:**
- Modify: `app/streamlit_app.py`
- Modify: `tests/test_streamlit_contract.py`
- Modify: `README.md`
- Modify: `reports/methodology/world-cup-forecasting-lab.md`

- [ ] **Step 1: Write the failing app contract tests**

```python
def test_streamlit_app_exposes_forecast_and_tournament_views() -> None:
    app_source = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")

    assert "Tournament Forecast" in app_source
    assert "Prediction vs Actual" in app_source
    assert "Group Scenarios" in app_source
    assert "Observed or Probable Lineup Context" in app_source
```

```python
def test_readme_describes_expanded_serving_artifacts() -> None:
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")

    assert "match_prediction_vs_actual.csv" in readme
    assert "group_forecast_summary.csv" in readme
```

- [ ] **Step 2: Run the public contract tests and verify they fail**

Run: `pytest tests/test_streamlit_contract.py tests/test_readme_contract.py -v`
Expected: FAIL because the app and docs still describe the product as an observed-truth-first shell with empty forecast tabs.

- [ ] **Step 3: Load the expanded serving outputs and add forecasting sections**

```python
from src.serving.load_outputs import (
    read_group_forecast_summary,
    read_knockout_forecast_summary,
    read_match_prediction_vs_actual,
    read_match_predictions,
    read_methodology_status,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_forecast_summary,
    read_team_summary,
)
```

```python
home_tab, coverage_tab, leaderboard_tab, match_tab, forecast_tab, teams_tab, methodology_tab = st.tabs(
    ["Home", "Coverage Summary", "Model Leaderboard", "Match Explorer", "Tournament Forecast", "Teams", "Methodology"]
)
```

```python
def _render_match_explorer(predictions: pd.DataFrame, comparisons: pd.DataFrame) -> None:
    st.subheader("Match Explorer")
    st.write("Observed or Probable Lineup Context")
    _render_dataframe(predictions, "No forecasts are available yet.")
    st.markdown("### Prediction vs Actual")
    _render_dataframe(comparisons, "No completed forecast comparisons are available yet.")
```

```python
def _render_tournament_forecast(groups: pd.DataFrame, knockout: pd.DataFrame) -> None:
    st.subheader("Tournament Forecast")
    st.markdown("### Group Scenarios")
    _render_dataframe(groups, "No group scenarios are available yet.")
    st.markdown("### Knockout Paths")
    _render_dataframe(knockout, "No knockout scenarios are available yet.")
```

- [ ] **Step 4: Update the public docs and methodology note**

```markdown
## Public Serving Outputs

- `observed_match_results.csv`: completed-match truth with current source coverage
- `match_predictions.csv`: match-level forecast rows for played and future matches
- `match_prediction_vs_actual.csv`: scored comparisons for already played matches
- `group_forecast_summary.csv`: projected group standings and advancement context
- `knockout_forecast_summary.csv`: projected knockout progression context
```

```markdown
## Observed vs Probable Context

Completed matches use observed lineup and substitution context where available. Future matches use probable lineup aggregates and are explicitly labeled as inferred rather than observed.
```

- [ ] **Step 5: Re-run the public contract tests**

Run: `pytest tests/test_streamlit_contract.py tests/test_readme_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit the public-app slice**

```bash
git add app/streamlit_app.py tests/test_streamlit_contract.py README.md reports/methodology/world-cup-forecasting-lab.md
git commit -m "feat: publish tournament forecasting app experience"
```

### Task 6: Run the end-to-end verification pass

**Files:**
- Modify: none
- Test: `tests/test_match_schema.py`
- Test: `tests/test_real_serving_snapshot.py`
- Test: `tests/test_team_match_features.py`
- Test: `tests/test_run_backtest.py`
- Test: `tests/test_evaluation_metrics.py`
- Test: `tests/test_serving_outputs.py`
- Test: `tests/test_streamlit_contract.py`
- Test: `tests/test_readme_contract.py`

- [ ] **Step 1: Run the targeted suite for the changed areas**

Run: `pytest tests/test_match_schema.py tests/test_real_serving_snapshot.py tests/test_team_match_features.py tests/test_run_backtest.py tests/test_evaluation_metrics.py tests/test_serving_outputs.py tests/test_streamlit_contract.py tests/test_readme_contract.py -v`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `pytest tests -v`
Expected: PASS with no regressions

- [ ] **Step 3: Validate the Streamlit entrypoint**

Run: `python -m py_compile app/streamlit_app.py`
Expected: no output

- [ ] **Step 4: Refresh the local serving snapshot**

Run: `python -m src.pipelines.build_real_serving_snapshot --start-date 2026-06-11 --end-date 2026-06-16 --disable-ssl-verification`
Expected: non-empty `match_predictions.csv`, `model_leaderboard.csv`, and tournament forecast artifacts in `data/serving/`

- [ ] **Step 5: Check git status before handoff**

Run: `git status --short`
Expected: clean working tree

- [ ] **Step 6: Create the final verification commit if any small regression fixes were needed**

```bash
git add -A
git commit -m "chore: finalize world cup event forecasting rollout"
```

Only run this step if the verification pass required a follow-up fix after the earlier task commits. Skip it if the tree is already clean.

## Self-Review

### Spec coverage

- Truth and future-fixture enrichment: covered by Task 1.
- Team and player-context feature generation: covered by Task 2.
- Event-first model and temporal evaluation outputs: covered by Task 3.
- Expanded public serving artifacts: covered by Task 4.
- Streamlit and documentation changes: covered by Task 5.
- Verification and regression safety: covered by Task 6.

### Placeholder scan

- No `TODO`, `TBD`, or deferred “implement later” placeholders remain.
- Each code-changing task includes concrete code examples and exact commands.

### Type consistency

- New artifact names remain consistent across pipeline, serving, app, and docs.
- The plan keeps `observed`, `probable`, and `unavailable` as separate semantic states instead of mixing them.
- The model outputs continue to use `model_name`, `target_name`, `predicted_value`, and `actual_value` consistently across evaluation and serving layers.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-16-world-cup-event-forecasting.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
