import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.feature_engineering import add_features
from src.scoring_model import calculate_scores
from src.squad_optimizer import select_best_xi, select_reserves, assign_squad_role
from src.tournament_predictor import compare_title_contenders_components

st.set_page_config(page_title="Brazil World Cup Data Lab", layout="wide", initial_sidebar_state="collapsed")

MIN_MINUTES = 300
SIMULATIONS = 10000

ROLE_LABELS = {
    "GK": "Goleiro", "RB": "Lateral direito", "CB": "Zagueiro", "LB": "Lateral esquerdo",
    "DM_CM": "Volante/Meio central", "RW": "Ponta direita", "AM_SS": "Meia/Segundo atacante",
    "LW": "Ponta esquerda", "ST": "Centroavante",
}
TACTICAL_LINES = [["ST"], ["LW", "AM_SS", "RW"], ["DM_CM", "DM_CM"], ["LB", "CB", "CB", "RB"], ["GK"]]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
:root{--bg:#030303;--ink:#f7f5ef;--soft:#c9c4ba;--muted:#817d74;--line:rgba(247,245,239,.14);--panel:rgba(255,255,255,.045);--acid:#d7ff6f;--blue:#9fc8ff;--red:#ff7777;}
.stApp{background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;}
.stApp:before{content:"";position:fixed;inset:0;background:radial-gradient(circle at 84% 5%,rgba(215,255,111,.12),transparent 26%),radial-gradient(circle at 5% 34%,rgba(159,200,255,.09),transparent 30%),linear-gradient(rgba(247,245,239,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(247,245,239,.025) 1px,transparent 1px);background-size:auto,auto,82px 82px,82px 82px;pointer-events:none;z-index:0;}
.block-container{padding-top:2.6rem;padding-bottom:4rem;max-width:1380px;position:relative;z-index:1;}
[data-testid="stSidebar"]{display:none;} h1,h2,h3,p,span,div{font-family:Inter,system-ui,sans-serif;}
.hero{border:1px solid var(--line);border-radius:38px;background:linear-gradient(135deg,rgba(255,255,255,.06),rgba(255,255,255,.018));box-shadow:0 24px 90px rgba(0,0,0,.32);padding:44px;margin-bottom:30px;min-height:365px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;position:relative;}
.hero:after{content:"";position:absolute;width:430px;height:430px;border-radius:50%;right:-140px;top:-120px;border:1px solid rgba(215,255,111,.18);background:radial-gradient(circle,rgba(215,255,111,.10),transparent 58%);}
.eyebrow{font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.16em;font-size:12px;color:var(--acid);font-weight:800;margin-bottom:18px;}
.hero-title{font-size:clamp(58px,7vw,118px);line-height:.84;letter-spacing:-.095em;font-weight:900;color:var(--ink);margin:0;max-width:1100px;position:relative;z-index:2;}
.hero-title em{font-style:normal;color:transparent;-webkit-text-stroke:1px rgba(247,245,239,.74);}
.hero-text{font-size:20px;line-height:1.42;color:#d7d2c8;max-width:1020px;margin-top:28px;letter-spacing:-.03em;position:relative;z-index:2;}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:9px 12px;margin:5px 6px 0 0;color:var(--soft);font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.08em;font-size:11px;background:rgba(255,255,255,.035);position:relative;z-index:2;}
.metric-card,.section-card,.rationale-card,.player-card,.case-card,.case-kpi,.data-card{border:1px solid var(--line);background:var(--panel);border-radius:24px;padding:22px;box-shadow:0 16px 48px rgba(0,0,0,.22);}
.metric-card{min-height:132px;} .metric-card span,.case-kpi span,.data-card span{display:block;color:var(--muted);font-family:'IBM Plex Mono',monospace;text-transform:uppercase;font-size:10px;letter-spacing:.09em;margin-bottom:8px;}
.metric-card strong,.case-kpi strong{display:block;font-size:34px;letter-spacing:-.06em;color:var(--ink);line-height:1;}
.muted{color:var(--soft);font-size:14px;line-height:1.55;}.section-title{margin:34px 0 16px;font-size:clamp(34px,4vw,60px);line-height:.94;letter-spacing:-.07em;font-weight:900;color:var(--ink);}.section-copy{color:var(--soft);font-size:17px;line-height:1.55;max-width:1020px;margin-bottom:24px;}
.pitch{border:1px solid var(--line);border-radius:38px;padding:30px;background:radial-gradient(circle at 50% 44%,rgba(215,255,111,.09),transparent 28%),linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.02));box-shadow:0 24px 80px rgba(0,0,0,.25);margin-bottom:26px;}
.player-card{min-height:156px;text-align:center;background:rgba(3,3,3,.76);display:flex;flex-direction:column;justify-content:center;gap:4px;}.player-role{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--acid);font-weight:800;text-transform:uppercase;letter-spacing:.09em;}.player-name{font-size:23px;color:var(--ink);font-weight:900;letter-spacing:-.045em;}.player-team{font-size:12px;color:var(--soft);}.player-score{font-size:14px;color:var(--ink);font-weight:800;margin-top:4px;}.player-reason{font-size:12px;color:#d7d2c8;line-height:1.25;}
.reason-title{font-size:19px;font-weight:850;color:var(--ink);letter-spacing:-.035em;margin-bottom:6px;}.reason-text,.case-card p,.case-card li,.data-card p{font-size:14px;color:var(--soft);line-height:1.55;}.case-hero{border:1px solid var(--line);border-radius:38px;background:linear-gradient(135deg,rgba(215,255,111,.075),rgba(255,255,255,.025));padding:34px;margin-bottom:22px;}.case-title{font-size:clamp(40px,5vw,76px);line-height:.9;letter-spacing:-.08em;font-weight:900;color:var(--ink);margin:0;max-width:1120px;}.case-lead{font-size:19px;line-height:1.42;color:#d7d2c8;max-width:1040px;margin-top:22px;letter-spacing:-.025em;}
.case-grid,.data-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px;}.case-card h3,.data-card h3{font-size:25px;letter-spacing:-.055em;line-height:1.05;margin:8px 0 12px;color:var(--ink);}.case-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0;} div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:18px;overflow:hidden;}.stTabs [data-baseweb="tab-list"]{gap:10px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px;}.stTabs [data-baseweb="tab"]{border:1px solid var(--line);border-radius:999px;padding:10px 16px;background:rgba(255,255,255,.035);color:var(--soft);font-family:'IBM Plex Mono',monospace;}.stTabs [aria-selected="true"]{background:var(--ink)!important;color:var(--bg)!important;}
@media(max-width:900px){.case-grid,.data-grid,.case-kpis{grid-template-columns:1fr}.hero{padding:26px;min-height:auto}.hero-title{font-size:52px}.pitch{padding:18px}}
</style>
""", unsafe_allow_html=True)


def load_players():
    return pd.read_csv(ROOT / "data" / "processed" / "sample_brazil_players.csv")

def load_source_comparison():
    return pd.read_csv(ROOT / "data" / "reference" / "source_comparison.csv")

def load_team_components():
    return pd.read_csv(ROOT / "data" / "reference" / "team_strength_components.csv")

def metric_card(label, value, note):
    st.markdown(f"<div class='metric-card'><span>{label}</span><strong>{value}</strong><div class='muted'>{note}</div></div>", unsafe_allow_html=True)

def compact_xi(xi):
    out = xi.copy()
    out["função"] = out["squad_position"].map(ROLE_LABELS)
    return out[["função", "player_name", "team", "league", "score_final", "minutes", "goals", "assists"]]

def best_metric(row):
    if row["squad_position"] in ["LW", "RW", "ST", "AM_SS"]:
        return f"{row['goal_contributions_p90']:.2f} participações em gol/90"
    if row["squad_position"] in ["DM_CM", "CB", "LB", "RB"]:
        return f"{row['duel_win_rate']:.0%} duelos vencidos · {row['tackles_p90']:.2f} desarmes/90"
    return f"{int(row['minutes'])} minutos · rating {row['rating']:.2f}"

def direct_competitor(row, df):
    role_df = df[df["squad_position"] == row["squad_position"]].sort_values("score_final", ascending=False)
    role_df = role_df[role_df["player_name"] != row["player_name"]]
    if role_df.empty:
        return "sem concorrente direto na base"
    comp = role_df.iloc[0]
    return f"à frente de {comp['player_name']} por {row['score_final'] - comp['score_final']:.1f} pontos"

def explain_choice(row, df):
    return f"Escolhido para {ROLE_LABELS.get(row['squad_position'], row['squad_position'])} porque fica no topo da função pelo score final ({row['score_final']:.1f}). O modelo valorizou {int(row['minutes'])} minutos, liga com peso {row['league_weight']:.2f}, rating {row['rating']:.2f} e {best_metric(row)}. Comparação direta: {direct_competitor(row, df)}."

def player_card(row):
    return f"""
    <div class='player-card'>
        <div class='player-role'>{ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div>
        <div class='player-name'>{row['player_name']}</div>
        <div class='player-team'>{row['team']} · {row['league']}</div>
        <div class='player-score'>Score {row['score_final']:.1f} · {int(row['minutes'])} min</div>
        <div class='player-reason'>{best_metric(row)}</div>
    </div>
    """

def render_tactical_board(xi):
    by_role = {role: xi[xi["squad_position"] == role].to_dict("records") for role in xi["squad_position"].unique()}
    used = {role: 0 for role in by_role}
    st.markdown("<div class='pitch'>", unsafe_allow_html=True)
    for line in TACTICAL_LINES:
        cols = st.columns(len(line))
        for i, role in enumerate(line):
            with cols[i]:
                idx = used.get(role, 0)
                players = by_role.get(role, [])
                if idx < len(players):
                    st.markdown(player_card(players[idx]), unsafe_allow_html=True)
                    used[role] = idx + 1
                else:
                    st.markdown("<div class='player-card'><div class='player-name'>Sem jogador</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def role_ranking(df):
    rows = []
    for role, label in ROLE_LABELS.items():
        subset = df[df["squad_position"] == role].sort_values("score_final", ascending=False).head(3)
        for rank, (_, row) in enumerate(subset.iterrows(), start=1):
            rows.append({"função": label, "rank": rank, "jogador": row["player_name"], "clube": row["team"], "liga": row["league"], "score": row["score_final"], "minutos": int(row["minutes"]), "gols": int(row["goals"]), "assistências": int(row["assists"]), "métrica-chave": best_metric(row)})
    return pd.DataFrame(rows)

raw_df = load_players()
raw_df = raw_df[raw_df["minutes"] >= MIN_MINUTES].copy()
df = assign_squad_role(calculate_scores(add_features(raw_df)))
xi = select_best_xi(df)
reserves = select_reserves(df, xi)
source_comparison = load_source_comparison()
team_components = load_team_components()
contenders = compare_title_contenders_components(team_components, simulations=SIMULATIONS, top_n=10)
brazil_row = contenders[contenders["team"] == "Brazil"].iloc[0]

avg_score = round(xi["score_final"].mean(), 1)
total_minutes = int(xi["minutes"].sum())
total_goals = int(xi["goals"].sum())
model_strength = round(float(brazil_row["model_strength"]), 1)

st.markdown("""
<div class='hero'>
  <div>
    <div class='eyebrow'>Football analytics / Data source comparison / World Cup 2026</div>
    <h1 class='hero-title'>Brazil squad logic, <em>with better data.</em></h1>
    <div class='hero-text'>A portfolio report comparing the current MVP data layer with a stronger SportsDataverse/worldfootballR strategy, then using a component-based model to estimate which national teams have the highest World Cup title probability.</div>
  </div>
  <div style='margin-top:28px'><span class='chip'>Python</span><span class='chip'>Streamlit</span><span class='chip'>worldfootballR candidate</span><span class='chip'>FBref / Transfermarkt / Understat</span><span class='chip'>Component model</span><span class='chip'>Monte Carlo</span></div>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1: metric_card("Score médio do XI", avg_score, "Média dos titulares sugeridos")
with m2: metric_card("Minutos do XI", f"{total_minutes:,}".replace(",", "."), "Ritmo competitivo agregado")
with m3: metric_card("Gols do XI", total_goals, "Produção recente da base")
with m4: metric_card("Força Brasil v2", model_strength, "Composto: elenco, forma, história e profundidade")

report_tab, sources_tab, forecast_tab, xi_tab, method_tab, api_tab, tables_tab = st.tabs(["Full report", "Data comparison", "Prediction model v2", "XI + Raciocínio", "Método estatístico", "Database/API", "Tabelas"])

with report_tab:
    st.markdown("<div class='case-hero'><div class='eyebrow'>Full model report / Portfolio case</div><div class='case-title'>A stronger data layer for Brazil's squad and World Cup forecast.</div><div class='case-lead'>The project now separates the MVP from the production-grade idea: the current dashboard remains reproducible with local CSV data, while the proposed data layer uses API-Football plus SportsDataverse/worldfootballR to bring richer player statistics and more defensible forecasting inputs.</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='case-kpis'><div class='case-kpi'><span>Current data</span><strong>CSV MVP</strong></div><div class='case-kpi'><span>New source</span><strong>worldfootballR</strong></div><div class='case-kpi'><span>Forecast</span><strong>Component model</strong></div><div class='case-kpi'><span>Simulation</span><strong>Monte Carlo</strong></div></div>", unsafe_allow_html=True)
    st.markdown("### What changes with the new data layer")
    st.markdown("The old MVP can explain the idea, but it does not fully support a serious selection model. The stronger version adds data depth: FBref-style per-90 metrics, Understat xG/xA, Transfermarkt market value and roster context, and potentially odds or Elo signals for team-strength benchmarking. This makes the selection logic less dependent on simple goals, assists and minutes.")
    st.markdown("### Why this makes player selection better")
    better_selection = pd.DataFrame([
        ["Attackers", "Goals and assists", "xG, xA, shots, key passes, shot quality, progressive actions"],
        ["Midfielders", "Goals, assists, tackles", "progression, creation, defensive work, passing profile, possession value"],
        ["Defenders", "duels, tackles, cards", "aerials, interceptions, pressures, progressive passes, defensive actions per 90"],
        ["Goalkeepers", "minutes and rating", "clean sheets, goals prevented, save rate, post-shot metrics when available"],
        ["Team forecast", "single strength index", "attack, midfield, defense, goalkeeper, form, history, market depth, confidence"],
    ], columns=["Decision area", "Current MVP", "Improved with richer sources"])
    st.dataframe(better_selection, use_container_width=True, hide_index=True)

with sources_tab:
    st.markdown("<div class='section-title'>Current API vs SportsDataverse layer</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>This comparison shows why the proposed SportsDataverse/worldfootballR layer matters. It does not replace a broad football API; it complements it with richer soccer-specific public data extraction.</div>", unsafe_allow_html=True)
    st.dataframe(source_comparison, use_container_width=True, hide_index=True)
    fig_sources = px.scatter(source_comparison, x="automation_fit", y="source", color="layer", size=[3]*len(source_comparison), hover_data=["coverage", "project_use"], labels={"automation_fit":"Automation fit", "source":"Source"})
    fig_sources.update_layout(height=470, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f5ef")
    st.plotly_chart(fig_sources, use_container_width=True)
    st.markdown("### Proposed production architecture")
    source_arch = pd.DataFrame([
        ["API-Football", "Primary automated ingestion", "IDs, clubs, competitions, fixtures, appearances and broad player-season stats."],
        ["worldfootballR / FBref", "Advanced performance layer", "Per-90 role metrics, creation, defensive actions and richer player profiles."],
        ["worldfootballR / Understat", "Expected-goals layer", "xG, xA and shot-quality context for attacking and creative players."],
        ["worldfootballR / Transfermarkt", "Squad and value enrichment", "Market value, player age, transfers and roster depth context."],
        ["Odds API / Elo / FIFA", "Benchmark layer", "External expectation to calibrate or compare tournament probability outputs."],
    ], columns=["Source", "Role", "Why it matters"])
    st.dataframe(source_arch, use_container_width=True, hide_index=True)

with forecast_tab:
    st.markdown("<div class='section-title'>Prediction model v2</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>The new model does not rely on one opaque strength value. It builds team strength from components: base strength, attack, midfield, defense, goalkeeper, recent form, tournament history, market depth and confidence.</div>", unsafe_allow_html=True)
    fig = px.bar(contenders, x="title_probability_pct", y="team", orientation="h", text="title_probability_pct", hover_data=["model_strength", "attack_score", "defense_score", "recent_form_score", "final_probability_pct"], labels={"title_probability_pct":"Chance de título (%)", "team":"Seleção"})
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(height=560, yaxis={"categoryorder":"total ascending"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f5ef", margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(contenders[["team", "model_strength", "title_probability_pct", "final_probability_pct", "semifinal_probability_pct", "attack_score", "midfield_score", "defense_score", "goalkeeper_score", "recent_form_score", "tournament_history_score", "market_depth_score"]], use_container_width=True, hide_index=True)
    st.markdown(f"<div class='section-card'><div class='reason-title'>Brazil readout</div><div class='reason-text'>Brazil's model strength is {brazil_row['model_strength']:.1f}. In this version, the title probability is {brazil_row['title_probability_pct']:.1f}% among the top-10 contenders, with {brazil_row['final_probability_pct']:.1f}% chance of reaching the final and {brazil_row['semifinal_probability_pct']:.1f}% chance of reaching the semifinal.</div></div>", unsafe_allow_html=True)

with xi_tab:
    st.markdown("<div class='section-title'>XI estatístico</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>Nomes, função, métrica-chave e justificativa. A versão futura com worldfootballR permite substituir métricas simples por xG, xA, progressão, criação e ações defensivas por 90.</div>", unsafe_allow_html=True)
    render_tactical_board(xi)
    st.markdown("### Por que esses 11 foram escolhidos")
    for _, row in xi.sort_values("squad_position").iterrows():
        st.markdown(f"<div class='rationale-card'><div class='reason-title'>{row['player_name']} — {ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div><div class='reason-text'>{explain_choice(row, df)}</div></div>", unsafe_allow_html=True)

with method_tab:
    st.markdown("<div class='section-title'>Método estatístico</div>", unsafe_allow_html=True)
    st.markdown("The player model selects by tactical role. The team forecast model now uses multiple components rather than one adjustable strength score.")
    st.code("""Player Score =
0.30 * role performance
+ 0.20 * minutes
+ 0.15 * league strength
+ 0.15 * recent form
+ 0.10 * national-team usage
+ 0.10 * tactical fit

Team Strength v2 =
0.25 * base strength
+ 0.17 * attack
+ 0.13 * midfield
+ 0.13 * defense
+ 0.08 * goalkeeper
+ 0.10 * recent form
+ 0.07 * tournament history
+ 0.07 * market depth""", language="text")
    st.markdown("#### Ranking por função")
    st.dataframe(role_ranking(df), use_container_width=True, hide_index=True)

with api_tab:
    st.markdown("<div class='section-title'>Database/API documentation</div>", unsafe_allow_html=True)
    schema = pd.DataFrame([
        ["players", "Dimension", "Player identity, nationality, age, preferred position."],
        ["teams", "Dimension", "Club, country, league and competition identifiers."],
        ["leagues", "Dimension", "League weights and competitive context."],
        ["player_season_stats", "Fact", "Minutes, goals, assists, passes, duels, cards, rating."],
        ["player_advanced_stats", "Fact", "xG, xA, progressive actions, pressures, shot creation, defensive activity."],
        ["player_market_value", "Reference", "Market value, squad depth and Transfermarkt context."],
        ["national_team_tests", "Fact", "Brazil lineups, position used, coach and tactical setup."],
        ["team_strength_components", "Model input", "Attack, midfield, defense, goalkeeper, form, history, depth and confidence."],
    ], columns=["Table", "Type", "Description"])
    st.dataframe(schema, use_container_width=True, hide_index=True)

with tables_tab:
    st.markdown("<div class='section-title'>Auditoria do elenco</div>", unsafe_allow_html=True)
    st.markdown("#### Titulares")
    st.dataframe(compact_xi(xi), use_container_width=True, hide_index=True)
    st.markdown("#### Reservas")
    st.dataframe(reserves[["player_name", "team", "league", "position", "score_final", "minutes", "goals", "assists", "rating"]], use_container_width=True, hide_index=True)
    st.markdown("#### Produção ofensiva x minutagem")
    fig_scatter = px.scatter(df, x="minutes", y="goal_contributions_p90", size="score_final", hover_name="player_name", color="league_weight", labels={"minutes":"Minutos", "goal_contributions_p90":"Gols + assistências por 90", "league_weight":"Peso da liga"})
    fig_scatter.update_layout(height=500, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f5ef")
    st.plotly_chart(fig_scatter, use_container_width=True)
