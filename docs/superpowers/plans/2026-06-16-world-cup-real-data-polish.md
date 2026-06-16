# World Cup Real-Data-Only Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stub-driven truth handling with a real-data-only flow that tracks source coverage and presents honest public-facing evaluation artifacts.

**Architecture:** Keep FIFA as the primary completed-match truth source, normalize that into coverage-aware team-match rows, then propagate coverage metadata into serving CSVs and the Streamlit app. Complementary APIs remain optional adapters, so the base product still works when only official score truth is available.

**Tech Stack:** Python, pandas, requests, pytest, Streamlit

---

## File Structure

- Modify: `src/ingestion/fifa_client.py`
  Responsibility: fetch accessible official FIFA page payloads and return normalized raw match dictionaries.
- Modify: `src/ingestion/fifa_parser.py`
  Responsibility: translate raw match payloads into two team-level rows with explicit truth coverage metadata.
- Modify: `src/pipelines/build_truth_dataset.py`
  Responsibility: define stable schema for truth rows, sort output, and persist coverage-aware truth datasets.
- Modify: `tests/test_fifa_parser.py`
  Responsibility: lock parser and truth dataset behavior for partial-metric coverage.
- Modify: `src/serving/load_outputs.py`
  Responsibility: write and read new serving artifacts including coverage summary and observed results.
- Modify: `tests/test_serving_outputs.py`
  Responsibility: lock serving output contracts for new CSVs and real-data-only filtering behavior.
- Modify: `app/streamlit_app.py`
  Responsibility: surface observed match counts, coverage status, and truth-aware empty states.
- Modify: `tests/test_streamlit_contract.py`
  Responsibility: assert that the public app exposes real-data messaging and coverage terminology.
- Modify: `README.md`
  Responsibility: explain real-data-only behavior, source hierarchy, and optional enrichment.
- Modify: `reports/methodology/world-cup-forecasting-lab.md`
  Responsibility: document production-style provenance, coverage rules, and current limitations.

### Task 1: Replace the truth stub with a coverage-aware FIFA ingestion flow

**Files:**
- Modify: `src/ingestion/fifa_client.py`
- Modify: `src/ingestion/fifa_parser.py`
- Modify: `src/pipelines/build_truth_dataset.py`
- Test: `tests/test_fifa_parser.py`

- [ ] **Step 1: Write the failing parser and dataset tests**

```python
def test_parse_team_match_rows_marks_partial_metric_coverage() -> None:
    raw_match = {
        "id": "match-003",
        "date": "2026-06-17",
        "stage": "group",
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": None,
        "shooting_source": None,
        "retrieved_at": "2026-06-16T22:00:00Z",
        "home_team": {"name": "Brazil", "goals": 3, "cards": None, "shots": None},
        "away_team": {"name": "Mexico", "goals": 1, "cards": None, "shots": None},
    }

    assert parse_team_match_rows(raw_match)[0] == {
        "match_id": "match-003",
        "match_date": "2026-06-17",
        "stage": "group",
        "team": "Brazil",
        "opponent": "Mexico",
        "is_home_team": True,
        "is_observed_match": True,
        "goals_for": 3,
        "cards_for": None,
        "shots_for": None,
        "has_goals_truth": True,
        "has_cards_truth": False,
        "has_shots_truth": False,
        "source": "fifa",
        "score_source": "fifa",
        "discipline_source": None,
        "shooting_source": None,
        "source_retrieved_at": "2026-06-16T22:00:00Z",
    }


def test_build_truth_dataset_returns_empty_dataframe_with_coverage_columns() -> None:
    dataset = build_truth_dataset([])

    assert list(dataset.columns) == [
        "match_id",
        "match_date",
        "stage",
        "team",
        "opponent",
        "is_home_team",
        "is_observed_match",
        "goals_for",
        "cards_for",
        "shots_for",
        "has_goals_truth",
        "has_cards_truth",
        "has_shots_truth",
        "source",
        "score_source",
        "discipline_source",
        "shooting_source",
        "source_retrieved_at",
    ]
```

- [ ] **Step 2: Run the focused test file to verify it fails**

Run: `pytest tests/test_fifa_parser.py -v`
Expected: FAIL because the parser and dataset schema do not yet expose the new coverage fields.

- [ ] **Step 3: Implement the minimal real-data-aware ingestion contract**

```python
class FIFAClient:
    BASE_URL = "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures"

    def fetch_world_cup_matches(self) -> list[dict]:
        response = requests.get(
            self.BASE_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
            verify=False,
        )
        response.raise_for_status()
        html = response.text
        return extract_match_payloads_from_page(html, retrieved_at=datetime.now(timezone.utc))
```

```python
def parse_team_match_rows(raw_match: dict) -> list[dict]:
    return [
        _build_team_row(raw_match, "home_team", "away_team", True),
        _build_team_row(raw_match, "away_team", "home_team", False),
    ]


def _build_team_row(raw_match: dict, team_key: str, opponent_key: str, is_home_team: bool) -> dict:
    team = raw_match[team_key]
    return {
        "match_id": raw_match["id"],
        "match_date": raw_match["date"],
        "stage": raw_match["stage"],
        "team": team["name"],
        "opponent": raw_match[opponent_key]["name"],
        "is_home_team": is_home_team,
        "is_observed_match": True,
        "goals_for": team.get("goals"),
        "cards_for": team.get("cards"),
        "shots_for": team.get("shots"),
        "has_goals_truth": team.get("goals") is not None,
        "has_cards_truth": team.get("cards") is not None,
        "has_shots_truth": team.get("shots") is not None,
        "source": raw_match.get("source", "fifa"),
        "score_source": raw_match.get("score_source"),
        "discipline_source": raw_match.get("discipline_source"),
        "shooting_source": raw_match.get("shooting_source"),
        "source_retrieved_at": raw_match.get("retrieved_at"),
    }
```

```python
TRUTH_DATASET_COLUMNS = [
    "match_id",
    "match_date",
    "stage",
    "team",
    "opponent",
    "is_home_team",
    "is_observed_match",
    "goals_for",
    "cards_for",
    "shots_for",
    "has_goals_truth",
    "has_cards_truth",
    "has_shots_truth",
    "source",
    "score_source",
    "discipline_source",
    "shooting_source",
    "source_retrieved_at",
]
```

- [ ] **Step 4: Re-run the focused ingestion tests**

Run: `pytest tests/test_fifa_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit the ingestion slice**

```bash
git add src/ingestion/fifa_client.py src/ingestion/fifa_parser.py src/pipelines/build_truth_dataset.py tests/test_fifa_parser.py
git commit -m "feat: add coverage-aware fifa truth ingestion"
```

### Task 2: Extend serving outputs with coverage summary and observed-result artifacts

**Files:**
- Modify: `src/serving/load_outputs.py`
- Test: `tests/test_serving_outputs.py`

- [ ] **Step 1: Write the failing serving output tests**

```python
def test_write_serving_outputs_creates_coverage_and_observed_result_csvs() -> None:
    coverage = pd.DataFrame([{"metric_name": "goals", "covered_rows": 8, "coverage_pct": 100.0}])
    observed = pd.DataFrame([{"match_id": "bra-vs-mex", "team": "Brazil", "goals_for": 3}])

    write_serving_outputs(
        temp_dir / "serving",
        leaderboard=leaderboard,
        predictions=predictions,
        teams=teams,
        coverage=coverage,
        observed_results=observed,
    )

    assert (temp_dir / "serving" / "coverage_summary.csv").exists()
    assert (temp_dir / "serving" / "observed_match_results.csv").exists()


def test_coverage_and_observed_result_readers_return_empty_frames_when_missing() -> None:
    serving_dir = _make_temp_dir() / "serving"

    assert read_coverage_summary(serving_dir).empty
    assert read_observed_match_results(serving_dir).empty
```

- [ ] **Step 2: Run the serving output tests to verify they fail**

Run: `pytest tests/test_serving_outputs.py -v`
Expected: FAIL because the writer and readers do not yet handle coverage or observed-result artifacts.

- [ ] **Step 3: Implement the serving artifact contract**

```python
def write_serving_outputs(
    base_dir: Path,
    leaderboard: pd.DataFrame,
    predictions: pd.DataFrame,
    teams: pd.DataFrame,
    coverage: pd.DataFrame,
    observed_results: pd.DataFrame,
) -> None:
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(output_dir / "model_leaderboard.csv", leaderboard)
    _write_csv(output_dir / "match_predictions.csv", predictions)
    _write_csv(output_dir / "team_summary.csv", teams)
    _write_csv(output_dir / "coverage_summary.csv", coverage)
    _write_csv(output_dir / "observed_match_results.csv", observed_results)


def read_coverage_summary(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "coverage_summary.csv")


def read_observed_match_results(base_dir: Path) -> pd.DataFrame:
    return _read_csv_or_empty(Path(base_dir) / "observed_match_results.csv")
```

- [ ] **Step 4: Re-run the serving tests**

Run: `pytest tests/test_serving_outputs.py -v`
Expected: PASS

- [ ] **Step 5: Commit the serving slice**

```bash
git add src/serving/load_outputs.py tests/test_serving_outputs.py
git commit -m "feat: add coverage-aware serving artifacts"
```

### Task 3: Make the public app explicitly real-data-only

**Files:**
- Modify: `app/streamlit_app.py`
- Modify: `tests/test_streamlit_contract.py`
- Modify: `README.md`
- Modify: `reports/methodology/world-cup-forecasting-lab.md`

- [ ] **Step 1: Write the failing public-app contract tests**

```python
def test_streamlit_app_exposes_real_data_coverage_language() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    ).read_text(encoding="utf-8")

    assert "Coverage Summary" in app_source
    assert "Observed Matches" in app_source
    assert "real-data-only" in app_source
```

- [ ] **Step 2: Run the Streamlit contract test**

Run: `pytest tests/test_streamlit_contract.py -v`
Expected: FAIL because the app does not yet surface coverage summary or real-data-only messaging.

- [ ] **Step 3: Update the app to load and display truth coverage**

```python
from src.serving.load_outputs import (
    read_coverage_summary,
    read_match_predictions,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_summary,
)


def _load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        read_model_leaderboard(SERVING_DIR),
        read_match_predictions(SERVING_DIR),
        read_team_summary(SERVING_DIR),
        read_coverage_summary(SERVING_DIR),
        read_observed_match_results(SERVING_DIR),
    )
```

```python
def _render_home(
    leaderboard: pd.DataFrame,
    predictions: pd.DataFrame,
    teams: pd.DataFrame,
    coverage: pd.DataFrame,
    observed_results: pd.DataFrame,
) -> None:
    st.title("World Cup Forecasting Lab")
    st.caption("real-data-only public layer with explicit source coverage")

    col1, col2, col3 = st.columns(3)
    col1.metric("Observed Matches", len(observed_results["match_id"].drop_duplicates()) if not observed_results.empty else 0)
    col2.metric("Forecast Rows", len(predictions))
    col3.metric("Coverage Metrics", len(coverage))

    _render_dataframe(
        coverage,
        "Coverage Summary is not available yet. Run the serving pipeline with real observed match truth.",
    )
```

```python
home_tab, coverage_tab, leaderboard_tab, match_tab, teams_tab, methodology_tab = st.tabs(
    ["Home", "Coverage Summary", "Model Leaderboard", "Match Explorer", "Teams", "Methodology"]
)
```

- [ ] **Step 4: Update the public documentation**

```markdown
## Real Data Contract

- Completed matches are sourced from official FIFA competition data whenever accessible.
- Score truth is never overwritten by secondary APIs.
- Cards, shots, and lineups remain null until a traceable public source is available.
- The public app exposes coverage artifacts so recruiters can see what is validated today versus what is waiting on more observed matches.
```

```markdown
## Provenance and Coverage

The product treats 2026 match truth as a layered data system: FIFA is the primary truth layer, while free public APIs can enrich non-score metrics when they are available and attributable. Missing advanced metrics are intentionally preserved as missing values rather than replaced with invented estimates.
```

- [ ] **Step 5: Run the public-facing regression tests**

Run: `pytest tests/test_streamlit_contract.py tests/test_readme_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit the product polish slice**

```bash
git add app/streamlit_app.py tests/test_streamlit_contract.py README.md reports/methodology/world-cup-forecasting-lab.md
git commit -m "feat: surface real-data coverage in public app"
```

### Task 4: Run the end-to-end verification pass

**Files:**
- Modify: none
- Test: `tests/test_fifa_parser.py`
- Test: `tests/test_serving_outputs.py`
- Test: `tests/test_streamlit_contract.py`
- Test: `tests/test_readme_contract.py`
- Test: `tests/test_team_match_features.py`
- Test: `tests/test_evaluation_metrics.py`

- [ ] **Step 1: Run the targeted suite for the changed areas**

Run: `pytest tests/test_fifa_parser.py tests/test_serving_outputs.py tests/test_streamlit_contract.py tests/test_readme_contract.py -v`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `pytest tests -v`
Expected: PASS with no regressions

- [ ] **Step 3: Check git status before handoff**

Run: `git status --short`
Expected: clean working tree

- [ ] **Step 4: Create the final polish commit if documentation or small follow-up fixes were needed during verification**

```bash
git add -A
git commit -m "chore: finalize real-data-only polish"
```

Only run this step if verification required an additional fix after the earlier task commits. Skip it if the tree is already clean.

## Self-Review

### Spec coverage

- Truth ingestion and coverage flags: covered by Task 1.
- Serving artifacts and truth-aware leaderboard behavior: covered by Task 2.
- Public app transparency and documentation: covered by Task 3.
- Verification and regression safety: covered by Task 4.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Each code-changing step includes concrete code snippets and exact commands.

### Type consistency

- Coverage artifact names remain consistent: `coverage_summary.csv` and `observed_match_results.csv`.
- Truth coverage fields remain consistent across parser, dataset, serving, and app layers: `has_goals_truth`, `has_cards_truth`, `has_shots_truth`.
