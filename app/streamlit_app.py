from pathlib import Path
import sys
from html import escape

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.serving.load_outputs import (
    read_match_predictions,
    read_coverage_summary,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_summary,
)

st.set_page_config(page_title="World Cup Forecasting Lab", layout="wide")

SERVING_DIR = ROOT / "data" / "serving"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }
        .hero-shell {
            background: linear-gradient(135deg, #0b3b3f 0%, #0f5c61 45%, #eef5f4 100%);
            border: 1px solid rgba(15, 92, 97, 0.18);
            border-radius: 24px;
            padding: 28px 30px;
            color: #f5fbfa;
            box-shadow: 0 24px 60px rgba(8, 41, 43, 0.16);
            margin-bottom: 1.2rem;
        }
        .hero-kicker {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 0.75rem;
            font-weight: 700;
            opacity: 0.82;
            margin-bottom: 10px;
        }
        .hero-title {
            font-size: 2.6rem;
            line-height: 1.02;
            font-weight: 700;
            margin: 0;
            max-width: 780px;
        }
        .hero-subtitle {
            margin-top: 14px;
            font-size: 1.02rem;
            line-height: 1.7;
            color: rgba(245, 251, 250, 0.9);
            max-width: 760px;
        }
        .section-heading {
            margin-top: 1.8rem;
            margin-bottom: 0.35rem;
            font-size: 1.4rem;
            font-weight: 700;
            color: #102a2c;
        }
        .section-copy {
            margin-bottom: 0.9rem;
            color: #4c6668;
            font-size: 0.98rem;
        }
        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin: 0.8rem 0 1.3rem 0;
        }
        .coverage-chip {
            padding: 0.78rem 0.95rem;
            border-radius: 999px;
            border: 1px solid rgba(15, 92, 97, 0.16);
            background: #ffffff;
            color: #15383b;
            min-width: 160px;
            box-shadow: 0 8px 24px rgba(10, 41, 43, 0.06);
        }
        .coverage-chip strong {
            display: block;
            font-size: 0.92rem;
            margin-bottom: 0.18rem;
        }
        .coverage-chip span {
            font-size: 0.86rem;
            color: #537072;
        }
        .coverage-chip.is-live {
            background: linear-gradient(180deg, #ffffff 0%, #eef8f7 100%);
            border-color: rgba(14, 130, 118, 0.24);
        }
        .coverage-chip.is-missing {
            background: linear-gradient(180deg, #ffffff 0%, #f7f3ef 100%);
            border-color: rgba(161, 104, 39, 0.18);
        }
        .scoreboard-grid, .architecture-grid, .publish-grid {
            display: grid;
            gap: 0.9rem;
        }
        .scoreboard-grid {
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            margin-bottom: 1.4rem;
        }
        .architecture-grid {
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            margin: 0.8rem 0 1.5rem 0;
        }
        .publish-grid {
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            margin: 0.8rem 0 1.2rem 0;
        }
        .scoreboard-card, .architecture-card, .publish-card {
            background: #ffffff;
            border: 1px solid rgba(15, 92, 97, 0.14);
            border-radius: 20px;
            padding: 1rem 1.05rem;
            box-shadow: 0 14px 34px rgba(11, 43, 45, 0.08);
        }
        .scoreboard-card {
            min-height: 190px;
        }
        .scoreboard-topline {
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #0f5c61;
            margin-bottom: 0.55rem;
        }
        .scoreboard-status {
            font-size: 0.82rem;
            color: #5c7578;
            margin-bottom: 0.9rem;
        }
        .scoreboard-team {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            padding: 0.34rem 0;
            border-bottom: 1px solid rgba(15, 92, 97, 0.08);
        }
        .scoreboard-team:last-of-type {
            border-bottom: none;
        }
        .scoreboard-team-name {
            font-size: 0.96rem;
            font-weight: 600;
            color: #142f31;
        }
        .scoreboard-score {
            font-size: 1.08rem;
            font-weight: 700;
            color: #0b3b3f;
        }
        .scoreboard-footer {
            margin-top: 0.85rem;
            font-size: 0.82rem;
            color: #60797c;
        }
        .architecture-card h4, .publish-card h4 {
            margin: 0 0 0.45rem 0;
            color: #0d383b;
            font-size: 1rem;
        }
        .architecture-card p, .publish-card p {
            margin: 0;
            color: #536e71;
            line-height: 1.65;
            font-size: 0.92rem;
        }
        .status-good {
            color: #0a7e61;
        }
        .status-waiting {
            color: #8f5c19;
        }
        .divider-space {
            height: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        read_model_leaderboard(SERVING_DIR),
        read_match_predictions(SERVING_DIR),
        read_team_summary(SERVING_DIR),
        read_coverage_summary(SERVING_DIR),
        read_observed_match_results(SERVING_DIR),
    )


def _render_empty_state(message: str) -> None:
    st.info(message)


def _render_dataframe(frame: pd.DataFrame, empty_message: str) -> None:
    if frame.empty:
        _render_empty_state(empty_message)
        return
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _count_observed_matches(observed_results: pd.DataFrame) -> int:
    if observed_results.empty:
        return 0
    if "match_id" in observed_results.columns:
        return int(observed_results["match_id"].nunique())
    return len(observed_results)


def _coverage_rows(coverage: pd.DataFrame) -> list[dict]:
    if coverage.empty:
        return []
    return coverage.to_dict("records")


def _recent_matches(observed_results: pd.DataFrame, limit: int = 6) -> pd.DataFrame:
    if observed_results.empty:
        return observed_results
    return observed_results.sort_values(
        ["match_date", "match_id"], ascending=[False, False]
    ).head(limit)


def _top_teams(teams: pd.DataFrame, limit: int = 6) -> pd.DataFrame:
    if teams.empty:
        return teams
    return teams.head(limit)


def _render_coverage_chips(coverage: pd.DataFrame) -> None:
    rows = _coverage_rows(coverage)
    if not rows:
        return

    html_parts = ['<div class="chip-row">']
    for row in rows:
        metric_name = escape(str(row.get("metric_name", "unknown")).title())
        coverage_pct = float(row.get("coverage_pct", 0.0))
        covered_matches = int(row.get("covered_matches", 0))
        total_matches = int(row.get("total_matches", 0))
        chip_class = "coverage-chip is-live" if bool(row.get("has_truth")) else "coverage-chip is-missing"
        html_parts.append(
            f"""
            <div class="{chip_class}">
              <strong>{metric_name}</strong>
              <span>{coverage_pct:.0f}% coverage · {covered_matches}/{total_matches} matches</span>
            </div>
            """
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_scoreboard_cards(observed_results: pd.DataFrame) -> None:
    st.markdown("### Recent Observed Matches")
    st.caption("Tournament status comes first: these are the latest completed matches in the current public truth layer.")
    if observed_results.empty:
        _render_empty_state(
            "No recent observed matches are available yet. The scoreboard cards appear as soon as completed matches enter the real-data truth layer."
        )
        return

    html_parts = ['<div class="scoreboard-grid">']
    for row in _recent_matches(observed_results).to_dict("records"):
        home_team = escape(str(row.get("home_team", "")))
        away_team = escape(str(row.get("away_team", "")))
        stage = escape(str(row.get("stage", "Unknown stage")))
        match_date = escape(str(row.get("match_date", "")))
        status = escape(str(row.get("status", "Final")))
        source = escape(str(row.get("source", "source")))
        home_goals = escape(str(row.get("home_goals", "")))
        away_goals = escape(str(row.get("away_goals", "")))
        shots_footer = ""
        if row.get("home_shots") == row.get("home_shots") and row.get("away_shots") == row.get("away_shots"):
            shots_footer = f"Shots: {int(row['home_shots'])}-{int(row['away_shots'])}"
        footer_text = f"{source.upper()} truth"
        if shots_footer:
            footer_text = f"{footer_text} · {shots_footer}"
        html_parts.append(
            f"""
            <div class="scoreboard-card">
              <div class="scoreboard-topline">{stage}</div>
              <div class="scoreboard-status">{match_date} · {status}</div>
              <div class="scoreboard-team">
                <span class="scoreboard-team-name">{home_team}</span>
                <span class="scoreboard-score">{home_goals}</span>
              </div>
              <div class="scoreboard-team">
                <span class="scoreboard-team-name">{away_team}</span>
                <span class="scoreboard-score">{away_goals}</span>
              </div>
              <div class="scoreboard-footer">{footer_text}</div>
            </div>
            """
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_methodology_cards() -> None:
    st.markdown("### What This Lab Is")
    st.caption("A dedicated methodology layer explains what is real today, what is still missing, and how the platform evaluates the tournament.")
    st.markdown(
        """
        <div class="architecture-grid">
          <div class="architecture-card">
            <h4>Truth Layer</h4>
            <p>Completed match truth is the foundation. The public app only surfaces tournament outcomes that have already happened and can be tied to a real observed source.</p>
          </div>
          <div class="architecture-card">
            <h4>Source Fallback</h4>
            <p>FIFA remains the preferred source when accessible. In this local environment, a public ESPN fallback keeps the serving snapshot populated with real observed tournament results.</p>
          </div>
          <div class="architecture-card">
            <h4>Coverage Policy</h4>
            <p>Coverage is explicit per target. Goals and shots can be published when observed, while cards remain intentionally unavailable until the source layer supports them honestly.</p>
          </div>
          <div class="architecture-card">
            <h4>Model Logic</h4>
            <p>The forecasting lab separates truth ingestion, serving outputs, and evaluation. Public-facing comparisons stay empty until enough observed match truth exists to support them fairly.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_publishability_status(leaderboard: pd.DataFrame, predictions: pd.DataFrame) -> None:
    st.markdown("### Publishability Status")
    leaderboard_ready = not leaderboard.empty
    predictions_ready = not predictions.empty
    st.markdown(
        f"""
        <div class="publish-grid">
          <div class="publish-card">
            <h4>Model Leaderboard</h4>
            <p class="{'status-good' if leaderboard_ready else 'status-waiting'}">
              {'Ready for public comparison with real truth coverage.' if leaderboard_ready else 'Waiting for enough observed match truth to support a fair public model ranking.'}
            </p>
          </div>
          <div class="publish-card">
            <h4>Forecast Publishing</h4>
            <p class="{'status-good' if predictions_ready else 'status-waiting'}">
              {'Forecast rows are currently publishable with coverage context.' if predictions_ready else 'Forecast rows stay unpublished until they can be paired with truthful tournament coverage and validation context.'}
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_top_teams_snapshot(teams: pd.DataFrame) -> None:
    st.markdown("### Top Teams Snapshot")
    st.caption("A compact standings-style readout from the observed results already loaded into the serving layer.")
    if teams.empty:
        _render_empty_state(
            "No top-team snapshot is available yet because the observed match layer has not produced enough team-level results."
        )
        return
    _render_dataframe(
        _top_teams(teams)[["team", "matches_played", "points", "goal_difference", "goals_for", "shots_for"]],
        "Top-team snapshot is not available yet.",
    )


def _render_home(
    leaderboard: pd.DataFrame,
    predictions: pd.DataFrame,
    teams: pd.DataFrame,
    coverage: pd.DataFrame,
    observed_results: pd.DataFrame,
) -> None:
    st.markdown(
        """
        <div class="hero-shell">
          <div class="hero-kicker">Tournament Status</div>
          <h1 class="hero-title">Real-time tournament intelligence built on observed World Cup truth.</h1>
          <p class="hero-subtitle">
            This home page acts as the executive front door of the lab: first the tournament status that is already real,
            then the methodology that explains what the platform can validate today and what still remains intentionally missing.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Observed Matches", _count_observed_matches(observed_results))
    col2.metric("Coverage Metrics", len(coverage))
    col3.metric("Leaderboard Rows", len(leaderboard))
    col4.metric("Forecasted Matches", len(predictions))
    col5.metric("Teams Profiled", len(teams))

    _render_coverage_chips(coverage)
    _render_scoreboard_cards(observed_results)
    _render_methodology_cards()
    _render_top_teams_snapshot(teams)
    _render_publishability_status(leaderboard, predictions)

    st.markdown("### Detailed Observed Match Table")
    st.caption("For scanability, the full observed truth layer remains available below after the visual tournament summary.")
    if not observed_results.empty:
        _render_dataframe(
            observed_results,
            "Observed match truth is expected here when completed matches have been collected.",
        )
    else:
        _render_empty_state(
            "No real observed match truth is available yet. Run the serving pipeline after "
            "completed matches are ingested so the public app stays real-data-only."
        )

    if coverage.empty:
        _render_empty_state(
            "Coverage Summary is not available yet. Run the serving pipeline with real observed "
            "match truth so the app can explain what has been validated."
        )


def _render_model_leaderboard(leaderboard: pd.DataFrame) -> None:
    st.subheader("Model Leaderboard")
    st.write("Track model-level evaluation outputs backed by real observed match truth.")
    _render_dataframe(
        leaderboard,
        "No leaderboard is published yet because there is not enough real observed match truth "
        "to support a public comparison.",
    )


def _render_match_explorer(predictions: pd.DataFrame) -> None:
    st.subheader("Match Explorer")
    st.write("Browse match-level forecasts alongside a public contract that only uses real data.")
    _render_dataframe(
        predictions,
        "No match forecasts are published yet. The public app only exposes forecasts that can be "
        "paired with real observed match truth and coverage metadata.",
    )


def _render_coverage_summary(coverage: pd.DataFrame) -> None:
    st.subheader("Coverage Summary")
    st.write(
        "Review which targets currently have real observed match truth and how much public "
        "coverage is available for each one."
    )
    _render_dataframe(
        coverage,
        "Coverage Summary is not available yet. Run the serving pipeline with real observed "
        "match truth to publish target-level coverage.",
    )


def _render_teams(teams: pd.DataFrame) -> None:
    st.subheader("Teams")
    st.write("Review team-level summary outputs generated from the real-data-only serving layer.")
    _render_dataframe(
        teams,
        "No team summary is published yet because the real observed match truth layer has not "
        "produced a public team view.",
    )


def _render_methodology() -> None:
    st.subheader("Methodology")
    st.write(
        "This app reads precomputed serving outputs instead of fitting models live in the "
        "UI. That keeps the experience stable while leaving training, evaluation, and batch "
        "forecast generation in the pipeline layer."
    )
    st.markdown(
        """
        - The public app is real-data-only: it only surfaces artifacts tied to real observed match truth.
        - `Coverage Summary` shows what has true observed coverage today versus what is still missing.
        - `Home` highlights observed matches first so the public status reflects truth coverage, not file presence.
        - `Model Leaderboard` is intended for model comparison artifacts.
        - `Match Explorer` is intended for match-level prediction rows.
        - `Teams` is intended for team summary outputs used in storytelling.
        - Empty states explain missing real observed match truth rather than implying generic missing CSV errors.
        """
    )


def main() -> None:
    _inject_styles()
    leaderboard, predictions, teams, coverage, observed_results = _load_outputs()
    home_tab, coverage_tab, leaderboard_tab, match_tab, teams_tab, methodology_tab = st.tabs(
        ["Home", "Coverage Summary", "Model Leaderboard", "Match Explorer", "Teams", "Methodology"]
    )

    with home_tab:
        _render_home(leaderboard, predictions, teams, coverage, observed_results)

    with coverage_tab:
        _render_coverage_summary(coverage)

    with leaderboard_tab:
        _render_model_leaderboard(leaderboard)

    with match_tab:
        _render_match_explorer(predictions)

    with teams_tab:
        _render_teams(teams)

    with methodology_tab:
        _render_methodology()


main()
