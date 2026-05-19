import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.feature_engineering import add_features
from src.scoring_model import calculate_scores
from src.squad_optimizer import select_best_xi, select_reserves, assign_squad_role
from src.tournament_predictor import compare_title_contenders_components

st.set_page_config(page_title="Brasil Copa Data Lab", layout="wide", initial_sidebar_state="collapsed")

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
:root{--bg:#030303;--ink:#f7f5ef;--soft:#c9c4ba;--muted:#817d74;--line:rgba(247,245,239,.14);--panel:rgba(255,255,255,.050);--acid:#d7ff6f;--blue:#9fc8ff;}
.stApp{background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;}
.stApp:before{content:"";position:fixed;inset:0;background:radial-gradient(circle at 84% 5%,rgba(215,255,111,.13),transparent 26%),radial-gradient(circle at 5% 34%,rgba(159,200,255,.09),transparent 30%),linear-gradient(rgba(247,245,239,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(247,245,239,.025) 1px,transparent 1px);background-size:auto,auto,82px 82px,82px 82px;pointer-events:none;z-index:0;}
.block-container{padding-top:2.6rem;padding-bottom:4rem;max-width:1400px;position:relative;z-index:1;}
[data-testid="stSidebar"]{display:none;} h1,h2,h3,p,span,div{font-family:Inter,system-ui,sans-serif;}
.hero{border:1px solid var(--line);border-radius:38px;background:linear-gradient(135deg,rgba(255,255,255,.065),rgba(255,255,255,.018));box-shadow:0 24px 90px rgba(0,0,0,.32);padding:46px;margin-bottom:30px;min-height:365px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;position:relative;}
.hero:after{content:"";position:absolute;width:430px;height:430px;border-radius:50%;right:-140px;top:-120px;border:1px solid rgba(215,255,111,.18);background:radial-gradient(circle,rgba(215,255,111,.10),transparent 58%);}
.eyebrow{font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.16em;font-size:12px;color:var(--acid);font-weight:800;margin-bottom:18px;}
.hero-title{font-size:clamp(58px,7vw,118px);line-height:.84;letter-spacing:-.095em;font-weight:900;color:var(--ink);margin:0;max-width:1100px;position:relative;z-index:2;}
.hero-title em{font-style:normal;color:transparent;-webkit-text-stroke:1px rgba(247,245,239,.74);}
.hero-text{font-size:20px;line-height:1.42;color:#d7d2c8;max-width:1040px;margin-top:28px;letter-spacing:-.03em;position:relative;z-index:2;}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:9px 12px;margin:5px 6px 0 0;color:var(--soft);font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.08em;font-size:11px;background:rgba(255,255,255,.035);position:relative;z-index:2;}
.metric-card,.section-card,.rationale-card,.player-card,.data-card{border:1px solid var(--line);background:var(--panel);border-radius:24px;padding:22px;box-shadow:0 16px 48px rgba(0,0,0,.22);}
.metric-card{min-height:132px}.metric-card span,.data-card span{display:block;color:var(--muted);font-family:'IBM Plex Mono',monospace;text-transform:uppercase;font-size:10px;letter-spacing:.09em;margin-bottom:8px}.metric-card strong{display:block;font-size:34px;letter-spacing:-.06em;color:var(--ink);line-height:1}.muted{color:var(--soft);font-size:14px;line-height:1.55}.section-title{margin:34px 0 16px;font-size:clamp(34px,4vw,60px);line-height:.94;letter-spacing:-.07em;font-weight:900;color:var(--ink)}.section-copy{color:var(--soft);font-size:17px;line-height:1.55;max-width:1060px;margin-bottom:24px}
.pitch{border:1px solid var(--line);border-radius:38px;padding:30px;background:radial-gradient(circle at 50% 44%,rgba(215,255,111,.09),transparent 28%),linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.02));box-shadow:0 24px 80px rgba(0,0,0,.25);margin-bottom:26px}.player-card{min-height:156px;text-align:center;background:rgba(3,3,3,.76);display:flex;flex-direction:column;justify-content:center;gap:4px}.player-role{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--acid);font-weight:800;text-transform:uppercase;letter-spacing:.09em}.player-name{font-size:23px;color:var(--ink);font-weight:900;letter-spacing:-.045em}.player-team{font-size:12px;color:var(--soft)}.player-score{font-size:14px;color:var(--ink);font-weight:800;margin-top:4px}.player-reason{font-size:12px;color:#d7d2c8;line-height:1.25}
.reason-title{font-size:19px;font-weight:850;color:var(--ink);letter-spacing:-.035em;margin-bottom:6px}.reason-text,.data-card p{font-size:14px;color:var(--soft);line-height:1.55}.data-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px}.data-card h3{font-size:25px;letter-spacing:-.055em;line-height:1.05;margin:8px 0 12px;color:var(--ink)}div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:18px;overflow:hidden}.stTabs [data-baseweb="tab-list"]{gap:10px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px}.stTabs [data-baseweb="tab"]{border:1px solid var(--line);border-radius:999px;padding:10px 16px;background:rgba(255,255,255,.035);color:var(--soft);font-family:'IBM Plex Mono',monospace}.stTabs [aria-selected="true"]{background:var(--ink)!important;color:var(--bg)!important}@media(max-width:900px){.data-grid{grid-template-columns:1fr}.hero{padding:26px;min-height:auto}.hero-title{font-size:52px}.pitch{padding:18px}}
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
    <div class='player-card'><div class='player-role'>{ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div><div class='player-name'>{row['player_name']}</div><div class='player-team'>{row['team']} · {row['league']}</div><div class='player-score'>Score {row['score_final']:.1f} · {int(row['minutes'])} min</div><div class='player-reason'>{best_metric(row)}</div></div>
    """

def render_tactical_board(xi):
    by_role = {role: xi[xi["squad_position"] == role].to_dict("records") for role in xi["squad_position"].unique()}
    used = {role: 0 for role in by_role}
    st.markdown("<div class='pitch'>", unsafe_allow_html=True)
    for line in TACTICAL_LINES:
        cols = st.columns(len(line))
        for i, role in enumerate(line):
            with cols[i]:
                idx = used.get(role, 0); players = by_role.get(role, [])
                st.markdown(player_card(players[idx]) if idx < len(players) else "<div class='player-card'><div class='player-name'>Sem jogador</div></div>", unsafe_allow_html=True)
                used[role] = idx + 1
    st.markdown("</div>", unsafe_allow_html=True)

def role_ranking(df):
    rows = []
    for role, label in ROLE_LABELS.items():
        subset = df[df["squad_position"] == role].sort_values("score_final", ascending=False).head(3)
        for rank, (_, row) in enumerate(subset.iterrows(), start=1):
            rows.append({"função": label, "rank": rank, "jogador": row["player_name"], "clube": row["team"], "liga": row["league"], "score": row["score_final"], "minutos": int(row["minutes"]), "gols": int(row["goals"]), "assistências": int(row["assists"]), "métrica-chave": best_metric(row)})
    return pd.DataFrame(rows)

def compact_xi(xi):
    out = xi.copy(); out["função"] = out["squad_position"].map(ROLE_LABELS)
    return out[["função", "player_name", "team", "league", "score_final", "minutes", "goals", "assists"]]

def style_plot(fig, height=520):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f5ef", margin=dict(l=10, r=10, t=25, b=10))
    return fig

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
<div class='hero'><div><div class='eyebrow'>Análise de futebol / fontes de dados / previsão Copa 2026</div><h1 class='hero-title'>Seleção brasileira, <em>explicada por dados.</em></h1><div class='hero-text'>Relatório de portfólio em português para comparar fontes de dados, justificar a escolha estatística do XI e estimar quais seleções têm maior chance de ganhar a Copa com um modelo composto e simulação Monte Carlo.</div></div><div style='margin-top:28px'><span class='chip'>Python</span><span class='chip'>Streamlit</span><span class='chip'>worldfootballR</span><span class='chip'>FBref / Transfermarkt / Understat</span><span class='chip'>Modelo composto</span><span class='chip'>Monte Carlo</span></div></div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1: metric_card("Score médio do XI", avg_score, "Média dos titulares sugeridos")
with m2: metric_card("Minutos do XI", f"{total_minutes:,}".replace(",", "."), "Ritmo competitivo agregado")
with m3: metric_card("Gols do XI", total_goals, "Produção recente da base")
with m4: metric_card("Força Brasil v2", model_strength, "Composição: elenco, forma, história e profundidade")

report_tab, sources_tab, forecast_tab, xi_tab, method_tab, api_tab, tables_tab = st.tabs(["Relatório", "Fontes de dados", "Previsão v2", "XI + raciocínio", "Método estatístico", "Database/API", "Tabelas"])

with report_tab:
    st.markdown("<div class='section-title'>Análise do projeto</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>O projeto já tem boa proposta de portfólio: combina dados, produto, narrativa, visual e tomada de decisão. A principal evolução agora é trocar uma prova de conceito baseada em CSV por uma arquitetura de dados mais robusta, com API-Football + SportsDataverse/worldfootballR, e justificar melhor os pesos do modelo.</div>", unsafe_allow_html=True)
    st.markdown("### O que a nova fonte melhora")
    better_selection = pd.DataFrame([
        ["Atacantes", "Gols, assistências e minutos", "xG, xA, finalizações, qualidade do chute, passes-chave e ações progressivas"],
        ["Meio-campistas", "Gols, assistências e desarmes", "progressão, criação, ações defensivas, perfil de passe e valor em posse"],
        ["Defensores", "Duelos, desarmes e cartões", "jogo aéreo, interceptações, pressão, passes progressivos e ações defensivas por 90"],
        ["Goleiros", "Minutos e rating", "clean sheets, taxa de defesa, gols evitados e métricas pós-finalização quando disponíveis"],
        ["Previsão", "um índice único de força", "força composta por ataque, meio, defesa, goleiro, forma, histórico e profundidade"],
    ], columns=["Área de decisão", "MVP atual", "Evolução com mais dados"])
    st.dataframe(better_selection, use_container_width=True, hide_index=True)

with sources_tab:
    st.markdown("<div class='section-title'>Comparativo de fontes</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>A camada SportsDataverse/worldfootballR não substitui uma API ampla: ela complementa o projeto com dados públicos mais ricos para futebol, especialmente via FBref, Transfermarkt e Understat.</div>", unsafe_allow_html=True)
    st.dataframe(source_comparison, use_container_width=True, hide_index=True)
    source_score = source_comparison.copy()
    source_score["cobertura_avancada"] = source_score["advanced_metrics"].map({"Strong": 3, "Medium": 2, "Basic only": 1, "Depends on package": 2, "No": 0}).fillna(1)
    source_score["automacao"] = source_score["automation_fit"].map({"High": 3, "Medium": 2, "Low": 1}).fillna(2)
    fig_sources = px.scatter(source_score, x="automacao", y="cobertura_avancada", size="automacao", color="layer", hover_name="source", hover_data=["coverage", "project_use"], labels={"automacao": "Facilidade de automação", "cobertura_avancada": "Profundidade analítica"})
    fig_sources.update_xaxes(tickvals=[1,2,3], ticktext=["baixa", "média", "alta"]); fig_sources.update_yaxes(tickvals=[0,1,2,3], ticktext=["nenhuma", "básica", "média", "forte"])
    st.plotly_chart(style_plot(fig_sources, 500), use_container_width=True)

with forecast_tab:
    st.markdown("<div class='section-title'>Previsão v2: candidatas ao título</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>A previsão agora usa força composta, em vez de um único índice. Isso permite enxergar por que uma seleção aparece bem: ataque, meio, defesa, goleiro, forma recente, histórico e profundidade.</div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.1, 1])
    with col1:
        fig = px.bar(contenders, x="title_probability_pct", y="team", orientation="h", text="title_probability_pct", hover_data=["model_strength", "final_probability_pct", "semifinal_probability_pct"], labels={"title_probability_pct":"Chance de título (%)", "team":"Seleção"})
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(style_plot(fig, 560), use_container_width=True)
    with col2:
        heat_cols = ["attack_score", "midfield_score", "defense_score", "goalkeeper_score", "recent_form_score", "tournament_history_score", "market_depth_score"]
        heat_df = contenders.set_index("team")[heat_cols]
        fig_heat = go.Figure(data=go.Heatmap(z=heat_df.values, x=["Ataque", "Meio", "Defesa", "Goleiro", "Forma", "Histórico", "Profundidade"], y=heat_df.index, coloraxis="coloraxis"))
        fig_heat.update_layout(coloraxis=dict(colorscale="Viridis"))
        st.plotly_chart(style_plot(fig_heat, 560), use_container_width=True)
    st.markdown("### Perfil comparativo: Brasil vs top 3")
    radar_teams = contenders.head(3)["team"].tolist()
    if "Brazil" not in radar_teams: radar_teams.append("Brazil")
    radar_source = contenders[contenders["team"].isin(radar_teams)]
    categories = ["attack_score", "midfield_score", "defense_score", "goalkeeper_score", "recent_form_score", "tournament_history_score", "market_depth_score"]
    labels = ["Ataque", "Meio", "Defesa", "Goleiro", "Forma", "Histórico", "Profundidade"]
    radar = go.Figure()
    for _, row in radar_source.iterrows():
        values = [row[c] for c in categories] + [row[categories[0]]]
        radar.add_trace(go.Scatterpolar(r=values, theta=labels + [labels[0]], fill="toself", name=row["team"]))
    radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[70, 100])), showlegend=True)
    st.plotly_chart(style_plot(radar, 560), use_container_width=True)

with xi_tab:
    st.markdown("<div class='section-title'>XI estatístico</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>O modelo compara jogadores dentro da mesma função tática. A versão futura com worldfootballR permite substituir métricas simples por xG, xA, progressão, criação e ações defensivas por 90.</div>", unsafe_allow_html=True)
    render_tactical_board(xi)
    st.markdown("### Justificativa por titular")
    for _, row in xi.sort_values("squad_position").iterrows():
        st.markdown(f"<div class='rationale-card'><div class='reason-title'>{row['player_name']} — {ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div><div class='reason-text'>{explain_choice(row, df)}</div></div>", unsafe_allow_html=True)

with method_tab:
    st.markdown("<div class='section-title'>Método estatístico</div>", unsafe_allow_html=True)
    st.markdown("""
O método combina quatro ideias comuns em análise esportiva: normalização por 90 minutos, seleção multicritério, modelos de força relativa entre equipes e simulação Monte Carlo. A proposta é manter o modelo explicável, não criar uma caixa-preta.

A seleção dos jogadores é feita por função tática. Isso é necessário porque um centroavante, um lateral e um volante têm formas diferentes de gerar valor. O modelo também penaliza baixa minutagem, pois pouca amostra aumenta o risco de superestimar desempenho.
""")
    st.code("""Player Score =
0.30 * performance por função
+ 0.20 * minutagem
+ 0.15 * força da liga
+ 0.15 * forma recente
+ 0.10 * uso na Seleção
+ 0.10 * encaixe tático

Team Strength v2 =
0.25 * força base
+ 0.17 * ataque
+ 0.13 * meio-campo
+ 0.13 * defesa
+ 0.08 * goleiro
+ 0.10 * forma recente
+ 0.07 * histórico em torneios
+ 0.07 * profundidade de elenco""", language="text")
    st.markdown("### Justificativa dos pesos")
    weights = pd.DataFrame([
        ["Performance por função", "0.30", "É a principal evidência de entrega técnica dentro do papel tático."],
        ["Minutagem", "0.20", "Controla ritmo competitivo e reduz risco de amostra pequena."],
        ["Força da liga", "0.15", "Contextualiza a dificuldade competitiva da produção."],
        ["Forma recente", "0.15", "Evita depender apenas de reputação ou histórico distante."],
        ["Uso na Seleção", "0.10", "Considera adaptação ao ambiente e às ideias da comissão."],
        ["Encaixe tático", "0.10", "Evita escolher bom jogador para função errada."],
    ], columns=["Componente", "Peso", "Justificativa"])
    st.dataframe(weights, use_container_width=True, hide_index=True)
    st.markdown("### Ranking por função")
    st.dataframe(role_ranking(df), use_container_width=True, hide_index=True)

with api_tab:
    st.markdown("<div class='section-title'>Database/API</div>", unsafe_allow_html=True)
    schema = pd.DataFrame([
        ["players", "Dimensão", "Identidade do jogador, nacionalidade, idade e posição preferencial."],
        ["teams", "Dimensão", "Clube, país, liga e identificadores de competição."],
        ["leagues", "Dimensão", "Pesos de liga e contexto competitivo."],
        ["player_season_stats", "Fato", "Minutos, gols, assistências, passes, duelos, cartões e rating."],
        ["player_advanced_stats", "Fato", "xG, xA, ações progressivas, pressão, criação de chutes e atividade defensiva."],
        ["player_market_value", "Referência", "Valor de mercado, profundidade de elenco e contexto Transfermarkt."],
        ["national_team_tests", "Fato", "Escalações do Brasil, posição usada, treinador e desenho tático."],
        ["team_strength_components", "Entrada do modelo", "Ataque, meio, defesa, goleiro, forma, histórico, profundidade e confiança."],
    ], columns=["Tabela", "Tipo", "Descrição"])
    st.dataframe(schema, use_container_width=True, hide_index=True)

with tables_tab:
    st.markdown("<div class='section-title'>Auditoria do elenco</div>", unsafe_allow_html=True)
    st.markdown("#### Titulares")
    st.dataframe(compact_xi(xi), use_container_width=True, hide_index=True)
    st.markdown("#### Reservas")
    st.dataframe(reserves[["player_name", "team", "league", "position", "score_final", "minutes", "goals", "assists", "rating"]], use_container_width=True, hide_index=True)
    fig_scatter = px.scatter(df, x="minutes", y="goal_contributions_p90", size="score_final", hover_name="player_name", color="league_weight", labels={"minutes":"Minutos", "goal_contributions_p90":"Gols + assistências por 90", "league_weight":"Peso da liga"})
    st.plotly_chart(style_plot(fig_scatter, 520), use_container_width=True)
