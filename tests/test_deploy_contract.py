from pathlib import Path


def test_deploy_assets_exist_for_stable_public_hosting() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    dockerfile = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    streamlit_config = (repo_root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    render_blueprint = (repo_root / "render.yaml").read_text(encoding="utf-8")

    assert "streamlit run app/streamlit_app.py" in dockerfile
    assert "enableCORS = false" in streamlit_config
    assert "enableXsrfProtection = false" in streamlit_config
    assert "runtime: docker" in render_blueprint
    assert "plan: starter" in render_blueprint
    assert "healthCheckPath: /" in render_blueprint
