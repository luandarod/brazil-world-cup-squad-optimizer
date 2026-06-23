from __future__ import annotations

from html import escape
from pathlib import Path
import sys
from textwrap import dedent

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.serving.load_outputs import (
    read_coverage_summary,
    read_group_forecast_summary,
    read_knockout_forecast_summary,
    read_match_prediction_vs_actual,
    read_match_predictions,
    read_methodology_status,
    read_model_leaderboard,
    read_observed_match_results,
    read_team_forecast_summary,
    read_team_summary,
    read_title_probability_summary,
    read_top_scorer_forecast,
)

st.set_page_config(page_title="Laboratório de Forecast da Copa", layout="wide")

SERVING_DIR = ROOT / "data" / "serving"
ROUND_ORDER = [
    "Round Of 32",
    "Round Of 16",
    "Quarterfinal",
    "Quarterfinals",
    "Semifinal",
    "Semifinals",
    "Third Place",
    "3Rd Place Match",
    "Final",
]
ROUND_LABELS = {
    "Round Of 32": "16 avos",
    "Round Of 16": "Oitavas",
    "Quarterfinal": "Quartas",
    "Quarterfinals": "Quartas",
    "Semifinal": "Semifinal",
    "Semifinals": "Semifinal",
    "Third Place": "3º lugar",
    "3Rd Place Match": "3º lugar",
    "Final": "Final",
}
MODEL_LABELS = {
    "hybrid-prior": "Híbrido pré-jogo + forma",
    "goals_for": "Gols",
    "shots_for": "Chutes",
    "cards_for": "Cartões",
    "fouls_for": "Faltas",
    "goals": "Gols",
    "shots": "Chutes",
    "cards": "Cartões",
    "fouls": "Faltas",
}
PUBLISH_STATUS_LABELS = {
    "published": "publicado",
    "forecast-only": "forecast público sem verdade completa",
    "truth-only": "verdade observada sem forecast público",
    "truth-unavailable": "sem verdade observada suficiente",
    "coverage-only": "somente cobertura",
}
TEAM_NAMES_PT = {
    "Algeria": "Argélia",
    "Argentina": "Argentina",
    "Australia": "Austrália",
    "Austria": "Áustria",
    "Belgium": "Bélgica",
    "Bosnia-Herzegovina": "Bósnia e Herzegovina",
    "Brazil": "Brasil",
    "Canada": "Canadá",
    "Cape Verde": "Cabo Verde",
    "Colombia": "Colômbia",
    "Congo DR": "RD Congo",
    "Croatia": "Croácia",
    "Curaçao": "Curaçao",
    "Czechia": "Tchéquia",
    "Ecuador": "Equador",
    "Egypt": "Egito",
    "England": "Inglaterra",
    "France": "França",
    "Germany": "Alemanha",
    "Ghana": "Gana",
    "Haiti": "Haiti",
    "Iran": "Irã",
    "Iraq": "Iraque",
    "Ivory Coast": "Costa do Marfim",
    "Japan": "Japão",
    "Jordan": "Jordânia",
    "Mexico": "México",
    "Morocco": "Marrocos",
    "Netherlands": "Países Baixos",
    "New Zealand": "Nova Zelândia",
    "Norway": "Noruega",
    "Panama": "Panamá",
    "Paraguay": "Paraguai",
    "Portugal": "Portugal",
    "Qatar": "Catar",
    "Saudi Arabia": "Arábia Saudita",
    "Scotland": "Escócia",
    "Senegal": "Senegal",
    "South Africa": "África do Sul",
    "South Korea": "Coreia do Sul",
    "Spain": "Espanha",
    "Sweden": "Suécia",
    "Switzerland": "Suíça",
    "Tunisia": "Tunísia",
    "Türkiye": "Turquia",
    "United States": "Estados Unidos",
    "Uruguay": "Uruguai",
    "Uzbekistan": "Uzbequistão",
}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

        :root {
            --bg: #f6f4ee;
            --surface: #fffdf8;
            --line: #d7dfd9;
            --ink: #10251f;
            --muted: #61756d;
            --teal-950: #0b2f28;
            --teal-900: #11483d;
            --teal-700: #18715e;
            --teal-100: #dbf0e8;
            --gold-100: #efe7d0;
            --shadow: 0 18px 40px rgba(10, 42, 35, 0.08);
            --radius-lg: 24px;
            --radius-md: 18px;
            --radius-sm: 14px;
        }
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(24, 113, 94, 0.10), transparent 24%),
                linear-gradient(180deg, #fbfaf6 0%, var(--bg) 100%);
            color: var(--ink);
            font-family: "IBM Plex Sans", sans-serif;
        }
        .block-container {
            max-width: 1340px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            padding: 0.55rem;
            margin-bottom: 1.2rem;
            border: 1px solid rgba(16, 37, 31, 0.10);
            border-radius: 18px;
            background: rgba(255, 253, 248, 0.92);
            box-shadow: 0 12px 28px rgba(10, 42, 35, 0.07);
            backdrop-filter: blur(10px);
        }
        .stTabs [data-baseweb="tab"] {
            min-height: 44px;
            padding: 0.55rem 0.95rem 0.5rem 0.95rem;
            border-radius: 12px;
            color: rgba(16, 37, 31, 0.72);
            font-family: "Barlow Condensed", sans-serif;
            font-size: 1.05rem;
            letter-spacing: 0.01em;
            transition: background-color 140ms ease, color 140ms ease, box-shadow 140ms ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(24, 113, 94, 0.08);
            color: var(--ink);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(180deg, rgba(24, 113, 94, 0.16) 0%, rgba(24, 113, 94, 0.10) 100%);
            color: var(--teal-950);
            box-shadow: inset 0 -2px 0 var(--teal-700);
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background: var(--teal-700);
            height: 3px;
            border-radius: 999px;
        }
        h1, h2, h3, h4, .kicker, .section-title, .metric-value, .match-score, .team-badge, .rank-number, .bracket-round-title {
            font-family: "Barlow Condensed", sans-serif;
            letter-spacing: 0.01em;
        }
        .hero-shell {
            position: relative;
            overflow: hidden;
            border-radius: 30px;
            padding: 2rem;
            margin-bottom: 1rem;
            background:
                linear-gradient(135deg, rgba(11, 47, 40, 0.98), rgba(17, 72, 61, 0.96));
            color: #f5f7f2;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 26px 68px rgba(11, 47, 40, 0.18);
        }
        .hero-shell::after {
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 14% 18%, rgba(255,255,255,0.09), transparent 18%),
                linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 48%, transparent 50%),
                repeating-linear-gradient(180deg, transparent 0 38px, rgba(255,255,255,0.05) 38px 39px);
            pointer-events: none;
            opacity: 0.55;
        }
        .kicker {
            text-transform: uppercase;
            font-size: 0.92rem;
            letter-spacing: 0.12em;
            color: rgba(245,247,242,0.82);
            margin-bottom: 0.55rem;
        }
        .hero-title {
            margin: 0;
            max-width: 860px;
            font-size: 3.3rem;
            line-height: 0.95;
        }
        .hero-copy {
            max-width: 820px;
            margin-top: 0.9rem;
            font-size: 1.02rem;
            line-height: 1.75;
            color: rgba(245,247,242,0.9);
        }
        .section-title {
            font-size: 2rem;
            margin: 1.2rem 0 0.2rem 0;
            color: var(--ink);
        }
        .section-copy {
            color: var(--muted);
            line-height: 1.65;
            margin-bottom: 0.85rem;
        }
        .card, .metric-card, .chip-card, .match-card, .rank-card, .method-card, .bracket-card, .table-shell, .status-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow);
        }
        .metric-card, .chip-card, .method-card, .status-card {
            padding: 1rem 1.05rem;
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .metric-value {
            display: block;
            margin-top: 0.35rem;
            font-size: 2.2rem;
            line-height: 1;
            color: var(--ink);
        }
        .metric-foot {
            margin-top: 0.25rem;
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.5;
        }
        .chip-title {
            font-size: 1.2rem;
            margin-bottom: 0.18rem;
        }
        .chip-copy {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.45;
        }
        .chip-card.is-soft {
            background: linear-gradient(180deg, #fffdf8 0%, #f7fbf9 100%);
        }
        .chip-card.is-warning {
            background: linear-gradient(180deg, #fffdf8 0%, #f4efe5 100%);
        }
        .match-card, .rank-card, .bracket-card {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .match-head, .bracket-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.85rem;
            color: var(--muted);
            font-size: 0.84rem;
        }
        .stage-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.22rem 0.6rem;
            border-radius: 999px;
            background: var(--teal-100);
            color: var(--teal-900);
            font-weight: 700;
        }
        .team-line {
            display: grid;
            grid-template-columns: 46px 1fr auto;
            gap: 0.7rem;
            align-items: center;
            padding: 0.42rem 0;
            border-bottom: 1px solid rgba(16,37,31,0.07);
        }
        .team-line:last-child {
            border-bottom: none;
        }
        .team-badge, .rank-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border-radius: 999px;
            background: rgba(24, 113, 94, 0.10);
            color: var(--teal-900);
            border: 1px solid rgba(24, 113, 94, 0.18);
            font-size: 1rem;
        }
        .team-name {
            font-size: 1rem;
            font-weight: 600;
            color: var(--ink);
        }
        .match-score {
            font-size: 1.55rem;
            color: var(--ink);
        }
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.55rem;
            margin-top: 0.85rem;
        }
        .meta-box {
            border-radius: var(--radius-sm);
            background: #eef4f0;
            padding: 0.45rem 0.55rem;
        }
        .meta-key {
            display: block;
            color: var(--muted);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .meta-value {
            display: block;
            color: var(--ink);
            margin-top: 0.12rem;
            font-weight: 700;
        }
        .winner-bar {
            margin-top: 0.9rem;
            display: inline-flex;
            align-items: center;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            background: var(--teal-100);
            color: var(--teal-900);
            font-size: 0.86rem;
            font-weight: 700;
        }
        .group-shell {
            padding: 1.05rem;
            margin-bottom: 1rem;
        }
        .group-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 0.8rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(16,37,31,0.07);
        }
        .group-row:last-child {
            border-bottom: none;
        }
        .group-main {
            display: flex;
            gap: 0.7rem;
            align-items: center;
        }
        .group-team {
            font-weight: 700;
        }
        .group-note {
            color: var(--muted);
            font-size: 0.86rem;
            margin-top: 0.05rem;
        }
        .group-stats {
            display: grid;
            grid-template-columns: repeat(5, minmax(48px, auto));
            gap: 0.35rem;
        }
        .group-stat {
            background: #eef4f0;
            border-radius: 12px;
            padding: 0.34rem 0.38rem;
            text-align: center;
        }
        .fixture-card {
            border: 1px solid rgba(16,37,31,0.08);
            border-radius: 16px;
            background: linear-gradient(180deg, #fffefb 0%, #f7faf8 100%);
            padding: 0.9rem;
            margin-bottom: 0.7rem;
        }
        .fixture-teams {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
            gap: 0.6rem;
            align-items: center;
        }
        .fixture-team {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            min-width: 0;
        }
        .fixture-team.is-away {
            justify-content: flex-end;
        }
        .fixture-score {
            font-family: "Barlow Condensed", sans-serif;
            font-size: 1.18rem;
            color: var(--ink);
        }
        .bracket-shell {
            overflow-x: auto;
            padding-bottom: 0.4rem;
        }
        .bracket-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(240px, 1fr));
            gap: 1rem;
            min-width: 1260px;
        }
        .bracket-round-title {
            font-size: 1.45rem;
            margin: 0 0 0.65rem 0;
        }
        .bracket-stack {
            display: grid;
            gap: 0.8rem;
        }
        .rank-card {
            display: grid;
            grid-template-columns: 48px minmax(0, 1fr) auto;
            gap: 0.8rem;
            align-items: center;
        }
        .rank-main {
            min-width: 0;
        }
        .rank-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--ink);
        }
        .rank-subtitle {
            color: var(--muted);
            font-size: 0.86rem;
            margin-top: 0.08rem;
        }
        .rank-value {
            text-align: right;
        }
        .rank-emphasis {
            font-family: "Barlow Condensed", sans-serif;
            font-size: 1.6rem;
            color: var(--ink);
            line-height: 1;
        }
        .rank-caption {
            color: var(--muted);
            font-size: 0.82rem;
        }
        .method-card h4 {
            margin: 0 0 0.32rem 0;
            font-size: 1.4rem;
        }
        .method-card p {
            margin: 0;
            color: var(--muted);
            line-height: 1.7;
        }
        .table-shell {
            padding: 0.9rem 1rem 1rem 1rem;
            margin-bottom: 1rem;
        }
        @media (max-width: 980px) {
            .hero-title {
                font-size: 2.5rem;
            }
            .meta-grid, .group-stats {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_outputs() -> dict[str, pd.DataFrame]:
    return {
        "leaderboard": read_model_leaderboard(SERVING_DIR),
        "predictions": read_match_predictions(SERVING_DIR),
        "teams": read_team_summary(SERVING_DIR),
        "coverage": read_coverage_summary(SERVING_DIR),
        "observed_results": read_observed_match_results(SERVING_DIR),
        "comparisons": read_match_prediction_vs_actual(SERVING_DIR),
        "group_forecast": read_group_forecast_summary(SERVING_DIR),
        "knockout_forecast": read_knockout_forecast_summary(SERVING_DIR),
        "team_forecast": read_team_forecast_summary(SERVING_DIR),
        "methodology_status": read_methodology_status(SERVING_DIR),
        "title_probability": read_title_probability_summary(SERVING_DIR),
        "top_scorers": read_top_scorer_forecast(SERVING_DIR),
    }


def _display_team(name: object) -> str:
    if name is None or pd.isna(name):
        return "-"
    return TEAM_NAMES_PT.get(str(name), str(name))


def _team_code(name: object) -> str:
    display_name = _display_team(name)
    parts = [part for part in display_name.replace("-", " ").split() if part]
    if not parts:
        return "---"
    if len(parts) == 1:
        return parts[0][:3].upper()
    return "".join(part[0] for part in parts[:3]).upper()


def _stage_label(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    text = str(value)
    if text.startswith("Group "):
        return text.replace("Group", "Grupo")
    return ROUND_LABELS.get(text, text)


def _model_label(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return MODEL_LABELS.get(str(value), str(value))


def _publish_status_label(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return PUBLISH_STATUS_LABELS.get(str(value), str(value).replace("-", " "))


def _format_date(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return pd.to_datetime(value).strftime("%d/%m/%Y")


def _format_number(value: object, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    number = float(value)
    if decimals == 0 or number.is_integer():
        return str(int(round(number)))
    return f"{number:.{decimals}f}"


def _format_pct(value: object, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.{decimals}f}%"


def _html(markup: str) -> None:
    st.html(dedent(markup).strip())


def _empty(message: str) -> None:
    st.info(message)


def _coverage_copy(row: dict[str, object], publish_status: str) -> tuple[str, str]:
    metric_name = str(row.get("metric_name", ""))
    covered_matches = int(float(row.get("covered_matches", 0) or 0))
    total_matches = int(float(row.get("total_matches", 0) or 0))
    coverage_pct = _format_pct(row.get("coverage_pct"), 0)

    if bool(row.get("has_truth")):
        return (
            f"{coverage_pct} de cobertura observada em {covered_matches}/{total_matches} partidas",
            "Leitura já comparável com a verdade do torneio.",
        )

    if publish_status == "forecast-only" and metric_name == "cards":
        return (
            "Forecast de cartões disponível para todos os jogos projetados.",
            "Ainda sem verdade observada confiável na fonte pública para validação jogo a jogo.",
        )

    return (
        f"Cobertura observada insuficiente em {covered_matches}/{total_matches} partidas",
        _publish_status_label(publish_status),
    )


def _winner_from_scores(home_team: object, away_team: object, home_score: object, away_score: object) -> str:
    if home_score is None or away_score is None or pd.isna(home_score) or pd.isna(away_score):
        return "-"
    if float(home_score) > float(away_score):
        return _display_team(home_team)
    if float(away_score) > float(home_score):
        return _display_team(away_team)
    return "Empate"


def _coverage_cards(coverage: pd.DataFrame, methodology_status: pd.DataFrame) -> None:
    if coverage.empty:
        return
    status_lookup = {}
    if not methodology_status.empty:
        status_lookup = methodology_status.set_index("metric_name")["publish_status"].to_dict()
    columns = st.columns(len(coverage.index))
    for column, row in zip(columns, coverage.to_dict("records")):
        publish_status = str(status_lookup.get(str(row.get("metric_name")), "coverage-only"))
        coverage_line, status_line = _coverage_copy(row, publish_status)
        css_class = "chip-card is-soft" if bool(row.get("has_truth")) else "chip-card is-warning"
        with column:
            _html(
                f"""
                <div class="{css_class}">
                  <div class="chip-title">{escape(_model_label(row.get("metric_name")))}</div>
                  <div class="chip-copy">{escape(coverage_line)}</div>
                  <div class="chip-copy">{escape(status_line)}</div>
                </div>
                """
            )


def _metric_strip(items: list[dict[str, str]]) -> None:
    columns = st.columns(len(items))
    for column, item in zip(columns, items):
        with column:
            _html(
                f"""
                <div class="metric-card">
                  <div class="metric-label">{escape(item["label"])}</div>
                  <span class="metric-value">{escape(item["value"])}</span>
                  <div class="metric-foot">{escape(item["foot"])}</div>
                </div>
                """
            )


def _match_card(row: dict, actual_mode: bool) -> str:
    home_goals = row.get("actual_home_goals") if actual_mode else row.get("predicted_home_goals", row.get("home_goals"))
    away_goals = row.get("actual_away_goals") if actual_mode else row.get("predicted_away_goals", row.get("away_goals"))
    home_shots = row.get("actual_home_shots") if actual_mode else row.get("predicted_home_shots", row.get("home_shots"))
    away_shots = row.get("actual_away_shots") if actual_mode else row.get("predicted_away_shots", row.get("away_shots"))
    home_cards = row.get("actual_home_cards") if actual_mode else row.get("predicted_home_cards", row.get("home_cards"))
    away_cards = row.get("actual_away_cards") if actual_mode else row.get("predicted_away_cards", row.get("away_cards"))
    home_fouls = row.get("actual_home_fouls") if actual_mode else row.get("predicted_home_fouls", row.get("home_fouls"))
    away_fouls = row.get("actual_away_fouls") if actual_mode else row.get("predicted_away_fouls", row.get("away_fouls"))
    winner = (
        row.get("actual_winner")
        if actual_mode and row.get("actual_winner") is not None
        else row.get("predicted_winner")
    )
    if not winner or pd.isna(winner):
        winner = _winner_from_scores(row.get("home_team"), row.get("away_team"), home_goals, away_goals)
    return f"""
        <div class="match-card">
          <div class="match-head">
            <span class="stage-pill">{escape(_stage_label(row.get("stage")))}</span>
            <span>{escape(_format_date(row.get("match_date")))}</span>
          </div>
          <div class="team-line">
            <span class="team-badge">{escape(_team_code(row.get("home_team")))}</span>
            <span class="team-name">{escape(_display_team(row.get("home_team")))}</span>
            <span class="match-score">{escape(_format_number(home_goals, 1))}</span>
          </div>
          <div class="team-line">
            <span class="team-badge">{escape(_team_code(row.get("away_team")))}</span>
            <span class="team-name">{escape(_display_team(row.get("away_team")))}</span>
            <span class="match-score">{escape(_format_number(away_goals, 1))}</span>
          </div>
          <div class="meta-grid">
            <div class="meta-box"><span class="meta-key">Chutes</span><span class="meta-value">{escape(_format_number(home_shots, 1))} x {escape(_format_number(away_shots, 1))}</span></div>
            <div class="meta-box"><span class="meta-key">Faltas</span><span class="meta-value">{escape(_format_number(home_fouls, 1))} x {escape(_format_number(away_fouls, 1))}</span></div>
            <div class="meta-box"><span class="meta-key">Cartões</span><span class="meta-value">{escape(_format_number(home_cards, 1))} x {escape(_format_number(away_cards, 1))}</span></div>
            <div class="meta-box"><span class="meta-key">Fonte</span><span class="meta-value">{escape("Real" if actual_mode else _model_label(row.get("model_name", "hybrid-prior")))}</span></div>
          </div>
          <div class="winner-bar">{escape("Resultado final" if actual_mode else "Cenário do modelo")}: {escape(_display_team(winner))}</div>
        </div>
    """


def _render_match_grid(frame: pd.DataFrame, actual_mode: bool, limit: int | None = None, empty_message: str = "Sem partidas para este recorte.") -> None:
    if frame.empty:
        _empty(empty_message)
        return
    rows = frame.to_dict("records")
    if limit is not None:
        rows = rows[:limit]
    for start in range(0, len(rows), 3):
        chunk = rows[start : start + 3]
        columns = st.columns(len(chunk))
        for column, row in zip(columns, chunk):
            with column:
                _html(_match_card(row, actual_mode=actual_mode))


def _prepare_table(frame: pd.DataFrame, column_map: dict[str, str], transforms: dict[str, callable]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    prepared = frame.copy()
    for column, transform in transforms.items():
        if column in prepared.columns:
            prepared[column] = prepared[column].map(transform)
    ordered = [column for column in column_map if column in prepared.columns]
    return prepared[ordered].rename(columns={column: column_map[column] for column in ordered})


def _render_table(frame: pd.DataFrame, column_map: dict[str, str], transforms: dict[str, callable], empty_message: str) -> None:
    if frame.empty:
        _empty(empty_message)
        return
    st.dataframe(
        _prepare_table(frame, column_map=column_map, transforms=transforms),
        use_container_width=True,
        hide_index=True,
    )


def _build_group_tables(observed_results: pd.DataFrame, predictions: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    future_groups = predictions.loc[
        predictions["is_future_fixture"].fillna(False)
        & predictions["stage"].astype(str).str.startswith("Group ")
    ].copy()
    rows: list[dict] = []
    for match in observed_results.to_dict("records"):
        if not str(match["stage"]).startswith("Group "):
            continue
        rows.extend(
            [
                _group_row(match["stage"], match["home_team"], match["home_goals"], match["away_goals"]),
                _group_row(match["stage"], match["away_team"], match["away_goals"], match["home_goals"]),
            ]
        )
    for match in future_groups.to_dict("records"):
        rows.extend(
            [
                _group_row(match["stage"], match["home_team"], match["predicted_home_goals"], match["predicted_away_goals"]),
                _group_row(match["stage"], match["away_team"], match["predicted_away_goals"], match["predicted_home_goals"]),
            ]
        )

    group_tables: dict[str, pd.DataFrame] = {}
    if rows:
        summary = pd.DataFrame(rows).groupby(["group_stage", "team"], as_index=False).sum(numeric_only=True)
        summary["saldo"] = summary["gp"] - summary["gc"]
        summary = summary.sort_values(
            ["group_stage", "pts", "saldo", "gp", "team"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        for group_stage, frame in summary.groupby("group_stage", sort=True):
            ordered = frame.reset_index(drop=True).copy()
            ordered["pos"] = range(1, len(ordered) + 1)
            group_tables[str(group_stage)] = ordered

    fixture_tables: dict[str, pd.DataFrame] = {}
    if not future_groups.empty:
        for group_stage, frame in future_groups.groupby("stage", sort=True):
            fixture_tables[str(group_stage)] = frame.sort_values(["match_date", "match_id"], kind="stable").reset_index(drop=True)
    return group_tables, fixture_tables


def _group_row(stage: object, team: object, goals_for: object, goals_against: object) -> dict:
    scored = float(goals_for or 0.0)
    conceded = float(goals_against or 0.0)
    return {
        "group_stage": str(stage),
        "team": str(team),
        "j": 1,
        "v": 1 if scored > conceded else 0,
        "e": 1 if scored == conceded else 0,
        "d": 1 if scored < conceded else 0,
        "gp": scored,
        "gc": conceded,
        "pts": 3 if scored > conceded else 1 if scored == conceded else 0,
    }


def _render_groups(observed_results: pd.DataFrame, predictions: pd.DataFrame) -> None:
    group_tables, fixture_tables = _build_group_tables(observed_results, predictions)
    if not group_tables:
        _empty("Ainda não há grupos suficientes para montar a leitura de torneio.")
        return

    for group_stage in sorted(group_tables):
        standings = group_tables[group_stage]
        fixtures = fixture_tables.get(group_stage, pd.DataFrame())
        left, right = st.columns([1.45, 1.05], gap="large")
        with left:
            rows_markup = []
            for row in standings.to_dict("records"):
                rows_markup.append(
                    f"""
                    <div class="group-row">
                      <div class="group-main">
                        <span class="rank-number">{int(row["pos"])}</span>
                        <div>
                          <div class="group-team">{escape(_display_team(row["team"]))}</div>
                          <div class="group-note">{int(row["pts"])} pts | {escape(_format_number(row["gp"], 0))} gols | saldo {escape(_format_number(row["saldo"], 0))}</div>
                        </div>
                      </div>
                      <div class="group-stats">
                        <div class="group-stat"><span class="meta-key">P</span><span class="meta-value">{int(row["pts"])}</span></div>
                        <div class="group-stat"><span class="meta-key">J</span><span class="meta-value">{int(row["j"])}</span></div>
                        <div class="group-stat"><span class="meta-key">V</span><span class="meta-value">{int(row["v"])}</span></div>
                        <div class="group-stat"><span class="meta-key">GP</span><span class="meta-value">{escape(_format_number(row["gp"], 0))}</span></div>
                        <div class="group-stat"><span class="meta-key">SG</span><span class="meta-value">{escape(_format_number(row["saldo"], 0))}</span></div>
                      </div>
                    </div>
                    """
                )
            _html(
                f"""
                <div class="group-shell card">
                  <div class="section-title" style="margin-top:0;">{escape(_stage_label(group_stage))}</div>
                  <div class="section-copy">Leitura do grupo consolidando o que já aconteceu com o que o modelo projeta para a rodada final.</div>
                  {''.join(rows_markup)}
                </div>
                """
            )
        with right:
            fixtures_markup = []
            if fixtures.empty:
                fixtures_markup.append(
                    """
                    <div class="fixture-card">
                      <div class="section-copy" style="margin-bottom:0;">Grupo já fechado. Não há partidas restantes neste recorte.</div>
                    </div>
                    """
                )
            else:
                for row in fixtures.to_dict("records"):
                    fixtures_markup.append(
                        f"""
                        <div class="fixture-card">
                          <div class="match-head">
                            <span class="stage-pill">{escape(_format_date(row.get("match_date")))}</span>
                            <span>placar projetado</span>
                          </div>
                          <div class="fixture-teams">
                            <div class="fixture-team">
                              <span class="team-badge">{escape(_team_code(row.get("home_team")))}</span>
                              <span class="team-name">{escape(_display_team(row.get("home_team")))}</span>
                            </div>
                            <span class="fixture-score">{escape(_format_number(row.get("predicted_home_goals"), 1))} x {escape(_format_number(row.get("predicted_away_goals"), 1))}</span>
                            <div class="fixture-team is-away">
                              <span class="team-name">{escape(_display_team(row.get("away_team")))}</span>
                              <span class="team-badge">{escape(_team_code(row.get("away_team")))}</span>
                            </div>
                          </div>
                          <div class="winner-bar">Mais provável: {escape(_display_team(row.get("predicted_winner")))}</div>
                        </div>
                        """
                    )
            _html(
                f"""
                <div class="group-shell card">
                  <div class="section-title" style="margin-top:0;">Rodada decisiva</div>
                  <div class="section-copy">Jogos restantes do grupo em formato de confronto, não apenas em tabela.</div>
                  {''.join(fixtures_markup)}
                </div>
                """
            )


def _render_bracket(knockout_forecast: pd.DataFrame) -> None:
    if knockout_forecast.empty:
        _empty("O caminho do mata-mata ainda não está disponível neste snapshot.")
        return

    rounds = {}
    ordered = knockout_forecast.copy()
    ordered["round_order"] = ordered["stage"].map({name: index for index, name in enumerate(ROUND_ORDER)}).fillna(999)
    ordered = ordered.sort_values(["round_order", "match_date", "match_id"], kind="stable")
    for round_name, frame in ordered.groupby("stage", sort=False):
        rounds[str(round_name)] = frame.reset_index(drop=True)

    round_names = [round_name for round_name in ROUND_ORDER if round_name in rounds][:5]
    columns = st.columns(len(round_names), gap="medium")
    for column, round_name in zip(columns, round_names):
        with column:
            cards = []
            for row in rounds[round_name].to_dict("records"):
                cards.append(
                    f"""
                    <div class="bracket-card">
                      <div class="bracket-head">
                        <span class="stage-pill">{escape(_format_date(row.get("match_date")))}</span>
                        <span>{escape(_display_team(row.get("predicted_winner")))}</span>
                      </div>
                      <div class="team-line">
                        <span class="team-badge">{escape(_team_code(row.get("home_team")))}</span>
                        <span class="team-name">{escape(_display_team(row.get("home_team")))}</span>
                        <span class="match-score">{escape(_format_number(row.get("predicted_home_goals"), 1))}</span>
                      </div>
                      <div class="team-line">
                        <span class="team-badge">{escape(_team_code(row.get("away_team")))}</span>
                        <span class="team-name">{escape(_display_team(row.get("away_team")))}</span>
                        <span class="match-score">{escape(_format_number(row.get("predicted_away_goals"), 1))}</span>
                      </div>
                      <div class="meta-grid">
                        <div class="meta-box"><span class="meta-key">Chutes</span><span class="meta-value">{escape(_format_number(row.get("predicted_home_shots"), 1))} x {escape(_format_number(row.get("predicted_away_shots"), 1))}</span></div>
                        <div class="meta-box"><span class="meta-key">Faltas</span><span class="meta-value">{escape(_format_number(row.get("predicted_home_fouls"), 1))} x {escape(_format_number(row.get("predicted_away_fouls"), 1))}</span></div>
                        <div class="meta-box"><span class="meta-key">Cartões</span><span class="meta-value">{escape(_format_number(row.get("predicted_home_cards"), 1))} x {escape(_format_number(row.get("predicted_away_cards"), 1))}</span></div>
                        <div class="meta-box"><span class="meta-key">Modelo</span><span class="meta-value">{escape(_model_label(row.get("model_name")))}</span></div>
                      </div>
                    </div>
                    """
                )
            _html(
                f"""
                <div class="table-shell">
                  <div class="bracket-round-title">{escape(_stage_label(round_name))}</div>
                  <div class="section-copy">Caminho projetado da chave nesta etapa.</div>
                  <div class="bracket-stack">
                    {''.join(cards)}
                  </div>
                </div>
                """
            )


def _render_rank_cards(frame: pd.DataFrame, title_column: str, subtitle_builder: callable, value_builder: callable, limit: int = 10, empty_message: str = "Sem dados para este ranking.") -> None:
    if frame.empty:
        _empty(empty_message)
        return
    rows = frame.head(limit).to_dict("records")
    for start in range(0, len(rows), 2):
        chunk = rows[start : start + 2]
        columns = st.columns(len(chunk))
        for idx, (column, row) in enumerate(zip(columns, chunk), start=start + 1):
            with column:
                _html(
                    f"""
                    <div class="rank-card">
                      <span class="rank-number">{idx}</span>
                      <div class="rank-main">
                        <div class="rank-title">{escape(title_column(row))}</div>
                        <div class="rank-subtitle">{escape(subtitle_builder(row))}</div>
                      </div>
                      <div class="rank-value">
                        <div class="rank-emphasis">{escape(value_builder(row))}</div>
                      </div>
                    </div>
                    """
                )


def _render_home(outputs: dict[str, pd.DataFrame]) -> None:
    predictions = outputs["predictions"]
    observed_results = outputs["observed_results"]
    coverage = outputs["coverage"]
    methodology_status = outputs["methodology_status"]
    title_probability = outputs["title_probability"]
    top_scorers = outputs["top_scorers"]

    future_predictions = predictions.loc[predictions["is_future_fixture"].fillna(False)].copy()
    observed_matches = observed_results.sort_values(["match_date", "match_id"], ascending=[False, False], kind="stable")
    future_matches = future_predictions.sort_values(["match_date", "match_id"], kind="stable")

    _html(
        """
        <div class="hero-shell">
          <div class="kicker">Laboratório de forecast da Copa 2026</div>
          <h1 class="hero-title">Status do torneio primeiro, metodologia visível logo abaixo e previsões públicas pensadas como produto analítico.</h1>
          <div class="hero-copy">
            Esta home resume a Copa em uma leitura executiva: o que já aconteceu, o que o modelo híbrido projeta para os próximos jogos, quais seleções aparecem melhor posicionadas no caminho do título e como a camada de engenharia sustenta tudo isso com dados observados, sinais pré-jogo e contexto de elenco.
          </div>
        </div>
        """
    )

    _metric_strip(
        [
            {
                "label": "Partidas observadas",
                "value": str(int(observed_results["match_id"].nunique()) if not observed_results.empty else 0),
                "foot": "Jogos com resultado real já encerrado.",
            },
            {
                "label": "Forecasts restantes",
                "value": str(int(future_predictions["match_id"].nunique()) if not future_predictions.empty else 0),
                "foot": "Confrontos ainda abertos no torneio.",
            },
            {
                "label": "Seleções modeladas",
                "value": str(int(pd.concat([observed_results[["home_team", "away_team"]], future_predictions[["home_team", "away_team"]]], ignore_index=True).stack().nunique()) if (not observed_results.empty or not future_predictions.empty) else 0),
                "foot": "Escopo total do snapshot público.",
            },
            {
                "label": "Prontidão analítica",
                "value": "alta" if not coverage.empty else "baixa",
                "foot": "Cobertura real para gols, chutes e faltas.",
            },
        ]
    )

    st.markdown("## Cobertura de métricas")
    st.caption("Gols, chutes, faltas e cartões aparecem com linguagem humana, sem expor nomes crus de variáveis.")
    _coverage_cards(coverage, methodology_status)

    st.markdown("## Partidas observadas mais recentes")
    st.caption("Leitura de placar em formato de card, incluindo chutes e disciplina por jogo.")
    _render_match_grid(observed_matches, actual_mode=True, limit=6, empty_message="Ainda não há jogos encerrados para este panorama.")

    st.markdown("## Próximos jogos com cenário de modelo")
    st.caption("O forecast agora nasce com um sinal híbrido pré-jogo + forma observada, e não apenas com média do que já aconteceu no torneio.")
    _render_match_grid(future_matches, actual_mode=False, limit=6, empty_message="Não há confrontos futuros publicados nesta base.")

    st.markdown("## Próximos passos mais prováveis do torneio")
    left, right = st.columns(2, gap="large")
    with left:
        _render_rank_cards(
            title_probability,
            title_column=lambda row: _display_team(row.get("team")),
            subtitle_builder=lambda row: f"força { _format_number(row.get('strength_rating'), 1) } | pontos projetados { _format_number(row.get('projected_total_points'), 1) }",
            value_builder=lambda row: _format_pct(row.get("title_probability_pct"), 1),
            limit=6,
            empty_message="Sem distribuição pública de título neste snapshot.",
        )
    with right:
        _render_rank_cards(
            top_scorers,
            title_column=lambda row: row.get("player_name", "-"),
            subtitle_builder=lambda row: f"{_display_team(row.get('team'))} | {row.get('position', '-')}",
            value_builder=lambda row: _format_number(row.get("projected_total_goals"), 1),
            limit=6,
            empty_message="Sem ranking público de artilharia nesta execução.",
        )

    st.markdown("## O que este laboratório faz")
    st.caption("A metodologia precisa estar visível na home, não escondida só na aba técnica.")
    method_columns = st.columns(4)
    method_cards = [
        (
            "Camada de verdade",
            "Resultados encerrados entram como observados. A aba de precisão compara previsão e realidade jogo a jogo.",
        ),
        (
            "Priors pré-jogo",
            "Cada seleção recebe um sinal híbrido com força prévia, contexto de elenco público, forma capturada no torneio e histórico recente de jogadores.",
        ),
        (
            "Stack de fontes",
            "ESPN sustenta placar e roster público, API-Football adiciona histórico recente de jogadores e a camada de serving preserva a origem de cada leitura.",
        ),
        (
            "Produto publicável",
            "Além do placar, o app expõe grupos, mata-mata, artilharia, título e metodologia em linguagem de negócio.",
        ),
    ]
    for column, (title, body) in zip(method_columns, method_cards):
        with column:
            _html(
                f"""
                <div class="method-card">
                  <h4>{escape(title)}</h4>
                  <p>{escape(body)}</p>
                </div>
                """
            )


def _render_predictions_tab(predictions: pd.DataFrame) -> None:
    future = predictions.loc[predictions["is_future_fixture"].fillna(False)].copy()
    st.markdown("## Cenários por jogo")
    st.caption("A aba central do produto: cenário provável por partida, com filtros por fase e seleção.")
    if future.empty:
        _empty("Ainda não há partidas futuras publicadas para esta aba.")
        return

    phases = ["Todas"] + sorted({_stage_label(value) for value in future["stage"].dropna().tolist()})
    teams = ["Todas"] + sorted({_display_team(value) for value in pd.concat([future["home_team"], future["away_team"]]).dropna().tolist()})
    filter_col_a, filter_col_b = st.columns(2)
    with filter_col_a:
        selected_phase = st.selectbox("Fase", phases, index=0)
    with filter_col_b:
        selected_team = st.selectbox("Seleção", teams, index=0)

    filtered = future.copy()
    if selected_phase != "Todas":
        filtered = filtered.loc[filtered["stage"].map(_stage_label) == selected_phase]
    if selected_team != "Todas":
        filtered = filtered.loc[
            (filtered["home_team"].map(_display_team) == selected_team)
            | (filtered["away_team"].map(_display_team) == selected_team)
        ]
    filtered = filtered.sort_values(["match_date", "match_id"], kind="stable")

    _render_match_grid(filtered, actual_mode=False, limit=9, empty_message="Nenhum jogo futuro atende aos filtros atuais.")

    st.markdown("### Explorer detalhado")
    _render_table(
        filtered,
        column_map={
            "match_date": "Dia do jogo",
            "stage": "Fase",
            "home_team": "Mandante",
            "away_team": "Visitante",
            "predicted_home_goals": "Gols mandante",
            "predicted_away_goals": "Gols visitante",
            "predicted_home_shots": "Chutes mandante",
            "predicted_away_shots": "Chutes visitante",
            "predicted_home_fouls": "Faltas mandante",
            "predicted_away_fouls": "Faltas visitante",
            "predicted_home_cards": "Cartões mandante",
            "predicted_away_cards": "Cartões visitante",
            "predicted_winner": "Cenário mais provável",
        },
        transforms={
            "match_date": _format_date,
            "stage": _stage_label,
            "home_team": _display_team,
            "away_team": _display_team,
            "predicted_home_goals": lambda value: _format_number(value, 1),
            "predicted_away_goals": lambda value: _format_number(value, 1),
            "predicted_home_shots": lambda value: _format_number(value, 1),
            "predicted_away_shots": lambda value: _format_number(value, 1),
            "predicted_home_fouls": lambda value: _format_number(value, 1),
            "predicted_away_fouls": lambda value: _format_number(value, 1),
            "predicted_home_cards": lambda value: _format_number(value, 1),
            "predicted_away_cards": lambda value: _format_number(value, 1),
            "predicted_winner": _display_team,
        },
        empty_message="Sem jogos futuros para detalhar.",
    )


def _render_accuracy_tab(comparisons: pd.DataFrame, leaderboard: pd.DataFrame) -> None:
    st.markdown("## Precisão até agora")
    st.caption("Só entra aqui o que já foi jogado. Nada de misturar cenário futuro com validação real.")
    total_games = int(comparisons["match_id"].nunique()) if not comparisons.empty else 0
    winner_hit_rate = float(comparisons["winner_hit"].mean() * 100.0) if not comparisons.empty else 0.0
    goals_mae = float(leaderboard.loc[leaderboard["target_name"] == "goals_for", "mae"].head(1).fillna(0.0).iloc[0]) if not leaderboard.empty and (leaderboard["target_name"] == "goals_for").any() else 0.0
    fouls_mae = float(leaderboard.loc[leaderboard["target_name"] == "fouls_for", "mae"].head(1).fillna(0.0).iloc[0]) if not leaderboard.empty and (leaderboard["target_name"] == "fouls_for").any() else 0.0
    _metric_strip(
        [
            {"label": "Jogos avaliados", "value": str(total_games), "foot": "Base pública usada na comparação."},
            {"label": "Acerto do vencedor", "value": _format_pct(winner_hit_rate, 0), "foot": "Taxa de acerto do cenário vencedor."},
            {"label": "MAE de gols", "value": _format_number(goals_mae, 2), "foot": "Erro médio absoluto por lado."},
            {"label": "MAE de faltas", "value": _format_number(fouls_mae, 2), "foot": "Disciplina de jogo validada com verdade observada."},
        ]
    )

    ordered = comparisons.sort_values(["match_date", "match_id"], ascending=[False, False], kind="stable")
    _render_match_grid(ordered, actual_mode=True, limit=6, empty_message="Ainda não há partidas suficientes para medir precisão.")

    st.markdown("### Leaderboard por estatística")
    _render_table(
        leaderboard,
        column_map={
            "model_name": "Modelo",
            "target_name": "Estatística",
            "observations": "Observações",
            "exact_hit_rate": "Acerto exato",
            "mae": "MAE",
            "rmse": "RMSE",
            "bias": "Bias",
        },
        transforms={
            "model_name": _model_label,
            "target_name": _model_label,
            "exact_hit_rate": lambda value: _format_pct(float(value) * 100.0, 1),
            "mae": lambda value: _format_number(value, 2),
            "rmse": lambda value: _format_number(value, 2),
            "bias": lambda value: _format_number(value, 2),
        },
        empty_message="O leaderboard ainda não tem observações suficientes.",
    )

    st.markdown("### Comparação jogo a jogo")
    _render_table(
        ordered,
        column_map={
            "match_date": "Dia do jogo",
            "stage": "Fase",
            "home_team": "Mandante",
            "away_team": "Visitante",
            "predicted_home_goals": "Prev. gols M",
            "actual_home_goals": "Real gols M",
            "predicted_away_goals": "Prev. gols V",
            "actual_away_goals": "Real gols V",
            "predicted_home_fouls": "Prev. faltas M",
            "actual_home_fouls": "Real faltas M",
            "predicted_away_fouls": "Prev. faltas V",
            "actual_away_fouls": "Real faltas V",
            "predicted_winner": "Prev. vencedor",
            "actual_winner": "Vencedor real",
            "winner_hit": "Acertou",
        },
        transforms={
            "match_date": _format_date,
            "stage": _stage_label,
            "home_team": _display_team,
            "away_team": _display_team,
            "predicted_home_goals": lambda value: _format_number(value, 1),
            "actual_home_goals": lambda value: _format_number(value, 0),
            "predicted_away_goals": lambda value: _format_number(value, 1),
            "actual_away_goals": lambda value: _format_number(value, 0),
            "predicted_home_fouls": lambda value: _format_number(value, 1),
            "actual_home_fouls": lambda value: _format_number(value, 0),
            "predicted_away_fouls": lambda value: _format_number(value, 1),
            "actual_away_fouls": lambda value: _format_number(value, 0),
            "predicted_winner": _display_team,
            "actual_winner": _display_team,
            "winner_hit": lambda value: "Sim" if float(value) >= 1.0 else "Não",
        },
        empty_message="Ainda não há partidas validadas nesta base.",
    )


def _render_models_tab(coverage: pd.DataFrame, methodology_status: pd.DataFrame, team_forecast: pd.DataFrame, group_forecast: pd.DataFrame) -> None:
    st.markdown("## Camada analítica pública")
    st.caption("A vitrine técnica dos artefatos que alimentam o app.")
    _coverage_cards(coverage, methodology_status)

    st.markdown("### Contrato metodológico")
    _render_table(
        methodology_status,
        column_map={
            "metric_name": "Estatística",
            "has_truth": "Tem verdade",
            "truth_coverage_pct": "Cobertura",
            "has_predictions": "Tem forecast",
            "publish_status": "Status público",
        },
        transforms={
            "metric_name": _model_label,
            "has_truth": lambda value: "Sim" if bool(value) else "Não",
            "truth_coverage_pct": lambda value: _format_pct(value, 0),
            "has_predictions": lambda value: "Sim" if bool(value) else "Não",
            "publish_status": _publish_status_label,
        },
        empty_message="Sem status metodológico para mostrar.",
    )

    st.markdown("### Fontes e construção do produto")
    st.caption("O app agora combina camada observada, priors estruturais e histórico recente de jogadores sem esconder a origem dos sinais.")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Camada": "Verdade observada",
                    "Origem principal": "ESPN scoreboard público",
                    "Uso no app": "Resultados, gols, chutes, faltas e comparação previsão vs. realidade.",
                },
                {
                    "Camada": "Priors de elenco",
                    "Origem principal": "ESPN roster público + API-Football",
                    "Uso no app": "Artilharia projetada, disciplina, peso ofensivo e profundidade recente por seleção.",
                },
                {
                    "Camada": "Serving analítico",
                    "Origem principal": "Pipelines e artefatos locais",
                    "Uso no app": "Grupos, mata-mata, probabilidade de título e cenários por jogo.",
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Projeção consolidada por seleção")
    _render_table(
        team_forecast,
        column_map={
            "team": "Seleção",
            "matches_played": "Jogos",
            "forecast_total_points": "Pontos finais",
            "forecast_total_goals_for": "Gols finais",
            "forecast_total_cards_for": "Cartões finais",
            "forecast_total_fouls_for": "Faltas finais",
        },
        transforms={
            "team": _display_team,
            "matches_played": lambda value: _format_number(value, 0),
            "forecast_total_points": lambda value: _format_number(value, 1),
            "forecast_total_goals_for": lambda value: _format_number(value, 1),
            "forecast_total_cards_for": lambda value: _format_number(value, 1),
            "forecast_total_fouls_for": lambda value: _format_number(value, 1),
        },
        empty_message="Sem resumo por seleção neste snapshot.",
    )

    st.markdown("### Cenário agregado dos grupos")
    _render_table(
        group_forecast,
        column_map={
            "group_stage": "Grupo",
            "team": "Seleção",
            "matches_played": "Jogos disputados",
            "matches_remaining": "Jogos restantes",
            "projected_total_points": "Pontos finais",
            "projected_total_goal_difference": "Saldo final",
        },
        transforms={
            "group_stage": _stage_label,
            "team": _display_team,
            "matches_played": lambda value: _format_number(value, 0),
            "matches_remaining": lambda value: _format_number(value, 0),
            "projected_total_points": lambda value: _format_number(value, 1),
            "projected_total_goal_difference": lambda value: _format_number(value, 1),
        },
        empty_message="Sem agregados de grupo disponíveis.",
    )


def _render_title_tab(title_probability: pd.DataFrame) -> None:
    st.markdown("## Porcentagem provável de ser campeão")
    st.caption("Sinal público de título combinando força prévia da seleção, caminho projetado e produção esperada no torneio.")
    _render_rank_cards(
        title_probability,
        title_column=lambda row: _display_team(row.get("team")),
        subtitle_builder=lambda row: f"força { _format_number(row.get('strength_rating'), 1) } | gols projetados { _format_number(row.get('projected_total_goals_for'), 1) }",
        value_builder=lambda row: _format_pct(row.get("title_probability_pct"), 1),
        limit=10,
        empty_message="Sem probabilidade pública de título nesta execução.",
    )
    st.markdown("### Distribuição completa")
    _render_table(
        title_probability,
        column_map={
            "team": "Seleção",
            "strength_rating": "Força",
            "projected_total_points": "Pontos projetados",
            "projected_total_goals_for": "Gols projetados",
            "title_probability_pct": "Prob. título",
            "final_probability_pct": "Prob. final",
            "semifinal_probability_pct": "Prob. semifinal",
        },
        transforms={
            "team": _display_team,
            "strength_rating": lambda value: _format_number(value, 1),
            "projected_total_points": lambda value: _format_number(value, 1),
            "projected_total_goals_for": lambda value: _format_number(value, 1),
            "title_probability_pct": lambda value: _format_pct(value, 1),
            "final_probability_pct": lambda value: _format_pct(value, 1),
            "semifinal_probability_pct": lambda value: _format_pct(value, 1),
        },
        empty_message="Sem tabela pública de título.",
    )


def _render_top_scorers_tab(top_scorers: pd.DataFrame) -> None:
    st.markdown("## Ranking projetado de gols")
    st.caption("Quem o laboratório projeta para terminar a Copa com mais gols, combinando produção atual, histórico recente de jogadores e o volume restante esperado da sua seleção.")
    _render_rank_cards(
        top_scorers,
        title_column=lambda row: row.get("player_name", "-"),
        subtitle_builder=lambda row: f"{_display_team(row.get('team'))} | {row.get('position', '-')}",
        value_builder=lambda row: _format_number(row.get("projected_total_goals"), 1),
        limit=10,
        empty_message="Sem ranking de artilharia nesta execução.",
    )
    st.markdown("### Explorer de artilharia")
    _render_table(
        top_scorers,
        column_map={
            "player_name": "Jogador",
            "team": "Seleção",
            "position": "Posição",
            "current_goals": "Gols atuais",
            "goal_share_pct": "Participação no gol",
            "projected_additional_goals": "Gols adicionais",
            "projected_total_goals": "Gols finais",
        },
        transforms={
            "team": _display_team,
            "current_goals": lambda value: _format_number(value, 1),
            "goal_share_pct": lambda value: _format_pct(value, 1),
            "projected_additional_goals": lambda value: _format_number(value, 2),
            "projected_total_goals": lambda value: _format_number(value, 2),
        },
        empty_message="Sem tabela de artilharia pública.",
    )


def _render_methodology_tab() -> None:
    st.markdown("## Como as previsões são feitas")
    st.caption("A aba dedicada à metodologia explica a construção do app e do modelo em linguagem de produto e engenharia.")
    columns = st.columns(4)
    cards = [
        (
            "Fonte observada",
            "Resultados reais vêm do placar público da ESPN. Gols, chutes e faltas já entram na camada de verdade assim que o jogo encerra.",
        ),
        (
            "Priors de seleção",
            "Cada time recebe um prior estrutural com força prévia, componentes de ataque e defesa e contexto de profundidade do elenco.",
        ),
        (
            "Priors de jogadores",
            "O app combina estatística pública de roster com API-Football para enriquecer artilharia projetada, faltas, cartões e o peso ofensivo de cada seleção.",
        ),
        (
            "Forecast híbrido",
            "O baseline público já não depende só da média do torneio. Ele mistura prior pré-jogo com forma recente e publica a comparação contra o que de fato aconteceu.",
        ),
    ]
    for column, (title, body) in zip(columns, cards):
        with column:
            _html(
                f"""
                <div class="method-card">
                  <h4>{escape(title)}</h4>
                  <p>{escape(body)}</p>
                </div>
                """
            )

    st.markdown(
        """
        1. A ingestão lê resultados concluídos e agenda futura da Copa até **19/07/2026**.
        2. A camada de features monta sinais de forma recente por time e injeta priors de seleção, elenco e histórico recente de jogadores.
        3. O baseline público atual é o **Híbrido pré-jogo + forma**, usado tanto no backtest quanto nas previsões futuras.
        4. O app publica três famílias de leitura: **cenário por jogo**, **caminho do torneio** e **camada analítica executiva**.
        5. A aba de **Precisão até agora** é atualizável jogo a jogo, sempre olhando apenas para partidas encerradas.
        """
    )
    st.markdown(
        """
        **Artefatos públicos deste app**

        - `observed_match_results.csv`
        - `match_predictions.csv`
        - `match_prediction_vs_actual.csv`
        - `group_forecast_summary.csv`
        - `knockout_forecast_summary.csv`
        - `team_forecast_summary.csv`
        - `title_probability_summary.csv`
        - `top_scorer_forecast.csv`
        - `methodology_status.csv`
        """
    )


def main() -> None:
    _inject_styles()
    outputs = _load_outputs()

    overview_tab, predictions_tab, accuracy_tab, groups_tab, knockout_tab, scorers_tab, title_tab, models_tab, methodology_tab = st.tabs(
        [
            "Panorama",
            "Cenários por Jogo",
            "Precisão até Agora",
            "Grupos",
            "Caminho do Mata-mata",
            "Artilharia Projetada",
            "Probabilidade de Título",
            "Camada Analítica",
            "Metodologia",
        ]
    )

    with overview_tab:
        _render_home(outputs)
    with predictions_tab:
        _render_predictions_tab(outputs["predictions"])
    with accuracy_tab:
        _render_accuracy_tab(outputs["comparisons"], outputs["leaderboard"])
    with groups_tab:
        _render_groups(outputs["observed_results"], outputs["predictions"])
    with knockout_tab:
        _render_bracket(outputs["knockout_forecast"])
    with scorers_tab:
        _render_top_scorers_tab(outputs["top_scorers"])
    with title_tab:
        _render_title_tab(outputs["title_probability"])
    with models_tab:
        _render_models_tab(
            outputs["coverage"],
            outputs["methodology_status"],
            outputs["team_forecast"],
            outputs["group_forecast"],
        )
    with methodology_tab:
        _render_methodology_tab()


main()
