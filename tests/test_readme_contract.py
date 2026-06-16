from pathlib import Path


def test_readme_describes_world_cup_forecasting_lab() -> None:
    readme_text = (
        Path(__file__).resolve().parents[1] / "README.md"
    ).read_text(encoding="utf-8").lower()

    assert "world cup forecasting lab" in readme_text
    assert "fifa official truth layer" in readme_text
    assert "market baseline" in readme_text
    assert "goals, cards, and shots" in readme_text
