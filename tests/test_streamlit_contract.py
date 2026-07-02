from pathlib import Path


def test_streamlit_app_exposes_forecast_and_tournament_views() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    ).read_text(encoding="utf-8")

    assert "Panorama" in app_source
    assert "Cenários por Jogo" in app_source
    assert "Precisão até Agora" in app_source
    assert "Grupos" in app_source
    assert "Caminho do Mata-mata" in app_source
    assert "Artilharia Projetada" in app_source
    assert "Probabilidade de Título" in app_source
    assert "Camada Analítica" in app_source
    assert "Metodologia" in app_source
    assert "Dia do jogo" in app_source
    assert "Estatística" in app_source
    assert "read_match_prediction_vs_actual" in app_source
    assert "read_group_forecast_summary" in app_source
    assert "read_knockout_forecast_summary" in app_source
    assert "read_team_forecast_summary" in app_source
    assert "read_methodology_status" in app_source
    assert "read_title_probability_summary" in app_source
    assert "read_top_scorer_forecast" in app_source
    assert "Laboratório de Forecast da Copa" in app_source
    assert "API-Football" in app_source
    assert "Priors de jogadores" in app_source
    assert "Otimizador de Escalação" in app_source


def test_public_docs_describe_expanded_serving_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    methodology_text = (
        repo_root / "reports" / "methodology" / "world-cup-forecasting-lab.md"
    ).read_text(encoding="utf-8")

    assert "match_prediction_vs_actual.csv" in readme_text
    assert "group_forecast_summary.csv" in readme_text
    assert "knockout_forecast_summary.csv" in readme_text
    assert "team_forecast_summary.csv" in readme_text
    assert "methodology_status.csv" in readme_text
    assert "title_probability_summary.csv" in readme_text
    assert "top_scorer_forecast.csv" in readme_text
    assert "Observed vs Probable Context" in readme_text
    assert "observed lineup and substitution context" in methodology_text
    assert "probable lineup aggregates" in methodology_text
    assert "API-Football" in methodology_text
    assert "player-history" in methodology_text
