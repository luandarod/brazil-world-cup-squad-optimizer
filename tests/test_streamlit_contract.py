from pathlib import Path


def test_streamlit_app_exposes_forecasting_tabs() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    ).read_text(encoding="utf-8")

    assert "Model Leaderboard" in app_source
    assert "Match Explorer" in app_source
    assert "Methodology" in app_source
