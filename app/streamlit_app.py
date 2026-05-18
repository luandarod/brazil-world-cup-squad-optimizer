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
from src.tournament_predictor import (
    compare_title_contenders,
    simulate_brazil_campaign,
    simulate_group_stage,
)

st.set_page_config(
    page_title="Brazil World Cup Data Lab",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROLE_LABELS = {
    "GK": "Goleiro", "RB": "Lateral direito", "CB": "Zagueiro", "LB": "Lateral esquerdo",
    "DM_CM": "Volante/Meio central", "RW": "Ponta direita", "AM_SS": "Meia/Segundo atacante",
    "LW": "Ponta esquerda", "ST": "Centroavante",
}

TACTICAL_LINES = [["ST"], ["LW", "AM_SS", "RW"], ["DM_CM", "DM_CM"], ["LB", "CB", "CB", "RB"], ["GK"]]

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
    :root{--bg:#030303;--ink:#f7f5ef;--soft:#c9c4ba;--muted:#817d74;--line:rgba(247,245,239,.14);--panel:rgba(255,255,255,.045);--acid:#d7ff6f;--blue:#9fc8ff;--red:#ff7777;}
    .stApp{background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;}
    .stApp:before{content:"";position:fixed;inset:0;background:radial-gradient(circle at 82% 4%,rgba(215,255,111,.11),transparent 25%),radial-gradient(circle at 8% 28%,rgba(159,200,255,.08),transparent 28%),linear-gradient(rgba(247,245,239,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(247,245,239,.025) 1px,transparent 1px);background-size:auto,auto,82px 82px,82px 82px;pointer-events:none;z-index:0;}
    .block-container{padding-top:2rem;max-width:1280px;position:relative;z-index:1;}
    h1,h2,h3,p,span,div{font-family:Inter,system-ui,sans-serif;}
    [data-testid="stSidebar"]{background:#070707;border-right:1px solid var(--line);}
    [data-testid="stSidebar"] *{color:var(--ink)!important;}
    .hero{border:1px solid var(--line);border-radius:34px;background:linear-gradient(135deg,rgba(255,255,255,.055),rgba(255,255,255,.018));box-shadow:0 24px 80px rgba(0,0,0,.28);padding:30px;margin-bottom:22px;}
    .eyebrow{font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.16em;font-size:12px;color:var(--acid);font-weight:800;margin-bottom:16px;}
    .hero-title{font-size:clamp(48px,7vw,104px);line-height:.86;letter-spacing:-.085em;font-weight:900;color:var(--ink);margin:0;max-width:980px;}
    .hero-title em{font-style:normal;color:transparent;-webkit-text-stroke:1px rgba(247,245,239,.72);}
    .hero-text{font-size:19px;line-height:1.35;color:#d7d2c8;max-width:900px;margin-top:24px;letter-spacing:-.03em;}
    .metric-card,.section-card,.rationale-card,.player-card,.pipeline-card{border:1px solid var(--line);background:var(--panel);border-radius:22px;padding:18px;box-shadow:0 14px 44px rgba(0,0,0,.18);}
    .metric-card strong{display:block;font-size:32px;letter-spacing:-.06em;color:var(--ink);}
    .metric-card span,.label{display:block;color:var(--muted);font-family:'IBM Plex Mono',monospace;text-transform:uppercase;font-size:10px;letter-spacing:.09em;margin-bottom:6px;}
    .muted{color:var(--soft);font-size:13px;line-height:1.45;}
    .pitch{border:1px solid var(--line);border-radius:34px;padding:22px;background:radial-gradient(circle at 50% 44%,rgba(215,255,111,.09),transparent 28%),linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.018));box-shadow:0 24px 80px rgba(0,0,0,.25);}
    .player-card{min-height:142px;text-align:center;background:rgba(3,3,3,.72);}
    .player-role{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--acid);font-weight:800;text-transform:uppercase;letter-spacing:.09em;}
    .player-name{font-size:22px;color:var(--ink);font-weight:900;letter-spacing:-.04em;margin-top:6px;}
    .player-team{font-size:12px;color:var(--soft);margin-top:3px;}
    .player-score{font-size:14px;color:var(--ink);font-weight:800;margin-top:9px;}
    .player-reason{font-size:12px;color:#d7d2c8;line-height:1.25;margin-top:5px;}
    .reason-title{font-size:18px;font-weight:850;color:var(--ink);letter-spacing:-.035em;margin-bottom:6px;}
    .reason-text{font-size:14px;color:var(--soft);line-height:1.5;}
    .chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:8px 10px;margin:4px;color:var(--soft);font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.08em;font-size:11px;background:rgba(255,255,255,.03);}
    div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:18px;overflow:hidden;}
    .stTabs [data-baseweb="tab-list"]{gap:8px;border-bottom:1px solid var(--line);}
    .stTabs [data-baseweb="tab"]{border:1px solid var(--line);border-radius:999px;padding:8px 14px;background:rgba(255,255,255,.03);color:var(--soft);font-family:'IBM Plex Mono',monospace;}
    .stTabs [aria-selected="true"]{background:var(--ink)!important;color:var(--bg)!important;}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_data(uploaded_file):
    sample_path = ROOT / "data" / "processed" / "sample_brazil_players.csv"
    return pd.read_csv(uploaded_file) if uploaded_file else pd.read_csv(sample_path)


def load_team_strength():
    return pd.read_csv(ROOT / "data" / "reference" / "team_strength_index.csv")


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
    diff = row["score_final"] - comp["score_final"]
    return f"à frente de {comp['player_name']} por {diff:.1f} pontos"


def explain_choice(row, df):
    return (
        f"Escolhido para {ROLE_LABELS.get(row['squad_position'], row['squad_position'])} porque fica no topo da função pelo score final "
        f"({row['score_final']:.1f}). O modelo valorizou {int(row['minutes'])} minutos, liga com peso {row['league_weight']:.2f}, "
        f"rating {row['rating']:.2f} e {best_metric(row)}. Comparação direta: {direct_competitor(row, df)}."
    )


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
            rows.append({
                "função": label,
                "rank": rank,
                "jogador": row["player_name"],
                "clube": row["team"],
                "liga": row["league"],
                "score": row["score_final"],
                "minutos": int(row["minutes"]),
                "gols": int(row["goals"]),
                "assistências": int(row["assists"]),
                "métrica-chave": best_metric(row),
            })
    return pd.DataFrame(rows)


st.markdown(
    """
    <div class='hero'>
      <div class='eyebrow'>Football analytics / Decision intelligence / World Cup 2026</div>
      <h1 class='hero-title'>Brazil squad logic, <em>made readable.</em></h1>
      <div class='hero-text'>
        Um laboratório de dados para explicar o XI estatístico do Brasil, documentar a arquitetura da base
        e comparar a Seleção com as 10 candidatas mais prováveis ao título.
      </div>
      <div style='margin-top:18px'>
        <span class='chip'>Python</span><span class='chip'>Streamlit</span><span class='chip'>PostgreSQL-ready</span><span class='chip'>Monte Carlo</span><span class='chip'>Squad scoring</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded = st.sidebar.file_uploader("Carregar CSV de jogadores", type=["csv"])
min_minutes = st.sidebar.slider("Minutagem mínima", min_value=0, max_value=3000, value=300, step=100)
brazil_strength = st.sidebar.slider("Índice de força do Brasil", min_value=70, max_value=100, value=92, step=1)
simulations = st.sidebar.select_slider("Simulações Monte Carlo", options=[1000, 5000, 10000, 25000], value=10000)

raw_df = load_data(uploaded)
raw_df = raw_df[raw_df["minutes"] >= min_minutes].copy()
df = assign_squad_role(calculate_scores(add_features(raw_df)))
xi = select_best_xi(df)
reserves = select_reserves(df, xi)
team_strength = load_team_strength()
team_strength.loc[team_strength["team"] == "Brazil", "strength_index"] = brazil_strength
contenders = compare_title_contenders(team_strength, simulations=simulations, top_n=10)

avg_score = round(xi["score_final"].mean(), 1)
total_minutes = int(xi["minutes"].sum())
total_goals = int(xi["goals"].sum())
total_assists = int(xi["assists"].sum())

m1, m2, m3, m4 = st.columns(4)
with m1: metric_card("Score médio do XI", avg_score, "Média dos titulares sugeridos")
with m2: metric_card("Minutos do XI", f"{total_minutes:,}".replace(",", "."), "Ritmo competitivo agregado")
with m3: metric_card("Gols do XI", total_goals, "Produção recente da base")
with m4: metric_card("Assistências", total_assists, "Criação direta de gols")

xi_tab, contenders_tab, method_tab, api_tab, tables_tab = st.tabs([
    "XI + Raciocínio", "Top 10 favoritas", "Método estatístico", "Database/API", "Tabelas"
])

with xi_tab:
    st.markdown("### XI estatístico — nomes, função e justificativa")
    render_tactical_board(xi)
    st.markdown("### Por que esses 11 foram escolhidos")
    for _, row in xi.sort_values("squad_position").iterrows():
        st.markdown(f"<div class='rationale-card'><div class='reason-title'>{row['player_name']} — {ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div><div class='reason-text'>{explain_choice(row, df)}</div></div>", unsafe_allow_html=True)

with contenders_tab:
    st.markdown("### As 10 seleções mais prováveis de ganhar a Copa")
    st.markdown("<div class='muted'>A comparação usa o índice de força das seleções e uma simulação Monte Carlo simplificada. A chance de título é normalizada entre as 10 maiores forças da base para facilitar a leitura comparativa.</div>", unsafe_allow_html=True)
    fig = px.bar(contenders, x="title_probability_pct", y="team", orientation="h", text="title_probability_pct", hover_data=["strength_index", "final_probability_pct", "semifinal_probability_pct"], labels={"title_probability_pct":"Chance de título (%)", "team":"Seleção"})
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(height=520, yaxis={"categoryorder":"total ascending"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f5ef", margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(contenders[["team", "strength_index", "title_probability_pct", "final_probability_pct", "semifinal_probability_pct"]], use_container_width=True, hide_index=True)

    brazil_row = contenders[contenders["team"] == "Brazil"]
    if not brazil_row.empty:
        r = brazil_row.iloc[0]
        st.markdown(f"<div class='section-card'><div class='reason-title'>Leitura do Brasil</div><div class='reason-text'>Com strength index {r['strength_index']:.0f}, o Brasil aparece com {r['title_probability_pct']:.1f}% de chance relativa de título entre as 10 candidatas analisadas. A chance estimada de final é {r['final_probability_pct']:.1f}% e a de semifinal é {r['semifinal_probability_pct']:.1f}%.</div></div>", unsafe_allow_html=True)

with method_tab:
    st.markdown("### Documentação do raciocínio estatístico")
    st.markdown("""
    O modelo trabalha em duas camadas. Primeiro, calcula a força individual dos jogadores por função. Depois, usa a força agregada do Brasil para comparar a Seleção com outras candidatas ao título.

    A escolha do XI segue esta lógica: filtra jogadores com minutagem mínima, cria métricas por 90 minutos, aplica peso por liga, normaliza tudo em escala comparável, calcula score final e seleciona o melhor jogador dentro de cada função do 4-2-3-1.
    """)
    st.code("""Score Final =
0.30 * performance por posição
+ 0.20 * minutagem
+ 0.15 * nível da liga
+ 0.15 * forma recente
+ 0.10 * uso/teste na Seleção
+ 0.10 * encaixe tático""", language="text")
    st.markdown("#### Ranking por função")
    rr = role_ranking(df)
    st.dataframe(rr, use_container_width=True, hide_index=True)

with api_tab:
    st.markdown("### Database/API documentation")
    schema = pd.DataFrame([
        ["players", "Dimensão", "Cadastro dos jogadores brasileiros elegíveis"],
        ["teams", "Dimensão", "Clubes, país e liga principal"],
        ["leagues", "Dimensão", "Peso competitivo de cada liga"],
        ["player_season_stats", "Fato", "Minutos, gols, assists, passes, duelos, cartões e rating"],
        ["national_team_tests", "Fato", "Jogos/testes da Seleção, formação e função usada"],
        ["player_scores", "Modelo", "Scores calculados por função e temporada"],
        ["team_strength_index", "Modelo", "Força estimada das seleções para simulação da Copa"],
    ], columns=["Tabela", "Tipo", "Descrição"])
    st.dataframe(schema, use_container_width=True, hide_index=True)
    st.markdown("""
    **Estrutura recomendada:** MVP em CSV + pandas; versão técnica em PostgreSQL; versão cloud em BigQuery + dbt/SQL. O app hoje lê CSV, mas a modelagem já está pronta para virar tabelas relacionais.
    """)
    st.markdown("#### Base carregada")
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

with tables_tab:
    st.markdown("### Auditoria do elenco")
    st.markdown("#### Titulares")
    st.dataframe(compact_xi(xi), use_container_width=True, hide_index=True)
    st.markdown("#### Reservas")
    st.dataframe(reserves[["player_name", "team", "league", "position", "score_final", "minutes", "goals", "assists", "rating"]], use_container_width=True, hide_index=True)
    st.markdown("#### Produção ofensiva x minutagem")
    fig_scatter = px.scatter(df, x="minutes", y="goal_contributions_p90", size="score_final", hover_name="player_name", color="league_weight", labels={"minutes":"Minutos", "goal_contributions_p90":"Gols + assistências por 90", "league_weight":"Peso da liga"})
    fig_scatter.update_layout(height=480, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f5ef")
    st.plotly_chart(fig_scatter, use_container_width=True)
