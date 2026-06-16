from pathlib import Path


def test_streamlit_app_exposes_forecasting_tabs() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    ).read_text(encoding="utf-8")

    assert "Tournament Status" in app_source
    assert "What This Lab Is" in app_source
    assert "Truth Layer" in app_source
    assert "Recent Observed Matches" in app_source
    assert "Publishability Status" in app_source
    assert "Top Teams Snapshot" in app_source
    assert "scoreboard-card" in app_source
    assert "read_coverage_summary" in app_source
    assert "read_observed_match_results" in app_source
    assert "Coverage Summary" in app_source
    assert "Model Leaderboard" in app_source
    assert "Match Explorer" in app_source
    assert "Observed Matches" in app_source
    assert "real observed match truth" in app_source
    assert "real-data-only" in app_source
    assert "Methodology" in app_source
