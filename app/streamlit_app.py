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
from src.tournament_predictor import compare_title_contenders

st.set_page_config(
    page_title="Brazil World Cup Data Lab",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MIN_MINUTES = 300
SIMULATIONS = 10000

ROLE_LABELS = {
    "GK": "Goleiro",
    "RB": "Lateral direito",
    "CB": "Zagueiro",
    "LB": "Lateral esquerdo",
    "DM_CM": "Volante/Meio central",
    "RW": "Ponta direita",
    "AM_SS": "Meia/Segundo atacante",
    "LW": "Ponta esquerda",
    "ST": "Centroavante",
}

TACTICAL_LINES = [
    ["ST"],
    ["LW", "AM_SS", "RW"],
    ["DM_CM", "DM_CM"],
    ["LB", "CB", "CB", "RB"],
    ["GK"],
]

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

    :root{
        --bg:#030303;
        --ink:#f7f5ef;
        --soft:#c9c4ba;
        --muted:#817d74;
        --line:rgba(247,245,239,.14);
        --panel:rgba(255,255,255,.045);
        --panel-2:rgba(255,255,255,.075);
        --acid:#d7ff6f;
        --blue:#9fc8ff;
        --red:#ff7777;
    }

    .stApp{
        background:var(--bg);
        color:var(--ink);
        font-family:Inter,system-ui,sans-serif;
    }

    .stApp:before{
        content:"";
        position:fixed;
        inset:0;
        background:
            radial-gradient(circle at 84% 5%,rgba(215,255,111,.12),transparent 26%),
            radial-gradient(circle at 5% 34%,rgba(159,200,255,.09),transparent 30%),
            linear-gradient(rgba(247,245,239,.025) 1px,transparent 1px),
            linear-gradient(90deg,rgba(247,245,239,.025) 1px,transparent 1px);
        background-size:auto,auto,82px 82px,82px 82px;
        pointer-events:none;
        z-index:0;
    }

    .block-container{
        padding-top:2.6rem;
        padding-bottom:4rem;
        max-width:1360px;
        position:relative;
        z-index:1;
    }

    [data-testid="stSidebar"]{display:none;}
    h1,h2,h3,p,span,div{font-family:Inter,system-ui,sans-serif;}

    .hero{
        border:1px solid var(--line);
        border-radius:38px;
        background:linear-gradient(135deg,rgba(255,255,255,.06),rgba(255,255,255,.018));
        box-shadow:0 24px 90px rgba(0,0,0,.32);
        padding:42px;
        margin-bottom:28px;
        min-height:360px;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        overflow:hidden;
        position:relative;
    }

    .hero:after{
        content:"";
        position:absolute;
        width:420px;
        height:420px;
        border-radius:50%;
        right:-130px;
        top:-110px;
        border:1px solid rgba(215,255,111,.18);
        background:radial-gradient(circle,rgba(215,255,111,.10),transparent 58%);
    }

    .eyebrow{
        font-family:'IBM Plex Mono',monospace;
        text-transform:uppercase;
        letter-spacing:.16em;
        font-size:12px;
        color:var(--acid);
        font-weight:800;
        margin-bottom:18px;
    }

    .hero-title{
        font-size:clamp(56px,7vw,116px);
        line-height:.84;
        letter-spacing:-.095em;
        font-weight:900;
        color:var(--ink);
        margin:0;
        max-width:1050px;
        position:relative;
        z-index:2;
    }

    .hero-title em{
        font-style:normal;
        color:transparent;
        -webkit-text-stroke:1px rgba(247,245,239,.74);
    }

    .hero-text{
        font-size:20px;
        line-height:1.38;
        color:#d7d2c8;
        max-width:980px;
        margin-top:28px;
        letter-spacing:-.03em;
        position:relative;
        z-index:2;
    }

    .chip{
        display:inline-block;
        border:1px solid var(--line);
        border-radius:999px;
        padding:9px 12px;
        margin:5px 6px 0 0;
        color:var(--soft);
        font-family:'IBM Plex Mono',monospace;
        text-transform:uppercase;
        letter-spacing:.08em;
        font-size:11px;
        background:rgba(255,255,255,.035);
        position:relative;
        z-index:2;
    }

    .metric-card,.section-card,.rationale-card,.player-card,.case-card,.case-kpi,.data-card{
        border:1px solid var(--line);
        background:var(--panel);
        border-radius:24px;
        padding:22px;
        box-shadow:0 16px 48px rgba(0,0,0,.22);
    }

    .metric-card{min-height:132px;}
    .metric-card span,.label,.case-kpi span,.data-card span{
        display:block;
        color:var(--muted);
        font-family:'IBM Plex Mono',monospace;
        text-transform:uppercase;
        font-size:10px;
        letter-spacing:.09em;
        margin-bottom:8px;
    }

    .metric-card strong,.case-kpi strong{
        display:block;
        font-size:34px;
        letter-spacing:-.06em;
        color:var(--ink);
        line-height:1;
    }

    .muted{color:var(--soft);font-size:14px;line-height:1.55;}

    .section-title{
        margin:34px 0 16px;
        font-size:clamp(32px,4vw,58px);
        line-height:.94;
        letter-spacing:-.07em;
        font-weight:900;
        color:var(--ink);
    }

    .section-copy{
        color:var(--soft);
        font-size:17px;
        line-height:1.55;
        max-width:980px;
        margin-bottom:22px;
    }

    .pitch{
        border:1px solid var(--line);
        border-radius:38px;
        padding:30px;
        background:radial-gradient(circle at 50% 44%,rgba(215,255,111,.09),transparent 28%),linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.02));
        box-shadow:0 24px 80px rgba(0,0,0,.25);
        margin-bottom:26px;
    }

    .player-card{
        min-height:156px;
        text-align:center;
        background:rgba(3,3,3,.76);
        display:flex;
        flex-direction:column;
        justify-content:center;
        gap:4px;
    }

    .player-role{
        font-family:'IBM Plex Mono',monospace;
        font-size:10px;
        color:var(--acid);
        font-weight:800;
        text-transform:uppercase;
        letter-spacing:.09em;
    }

    .player-name{
        font-size:23px;
        color:var(--ink);
        font-weight:900;
        letter-spacing:-.045em;
    }

    .player-team{font-size:12px;color:var(--soft);}
    .player-score{font-size:14px;color:var(--ink);font-weight:800;margin-top:4px;}
    .player-reason{font-size:12px;color:#d7d2c8;line-height:1.25;}

    .reason-title{
        font-size:19px;
        font-weight:850;
        color:var(--ink);
        letter-spacing:-.035em;
        margin-bottom:6px;
    }

    .reason-text,.case-card p,.case-card li,.data-card p{
        font-size:14px;
        color:var(--soft);
        line-height:1.55;
    }

    .case-hero{
        border:1px solid var(--line);
        border-radius:38px;
        background:linear-gradient(135deg,rgba(215,255,111,.075),rgba(255,255,255,.025));
        padding:34px;
        margin-bottom:22px;
    }

    .case-title{
        font-size:clamp(40px,5vw,76px);
        line-height:.9;
        letter-spacing:-.08em;
        font-weight:900;
        color:var(--ink);
        margin:0;
        max-width:1100px;
    }

    .case-lead{
        font-size:19px;
        line-height:1.42;
        color:#d7d2c8;
        max-width:1020px;
        margin-top:22px;
        letter-spacing:-.025em;
    }

    .case-grid,.data-grid{
        display:grid;
        grid-template-columns:repeat(2,minmax(0,1fr));
        gap:16px;
        margin-top:16px;
    }

    .case-card h3,.data-card h3{
        font-size:25px;
        letter-spacing:-.055em;
        line-height:1.05;
        margin:8px 0 12px;
        color:var(--ink);
    }

    .case-kpis{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:12px;
        margin:18px 0;
    }

    .report-block{border-top:1px solid var(--line);padding-top:24px;margin-top:28px;}

    div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:18px;overflow:hidden;}

    .stTabs [data-baseweb="tab-list"]{
        gap:10px;
        border-bottom:1px solid var(--line);
        padding-bottom:12px;
        margin-bottom:18px;
    }

    .stTabs [data-baseweb="tab"]{
        border:1px solid var(--line);
        border-radius:999px;
        padding:10px 16px;
        background:rgba(255,255,255,.035);
        color:var(--soft);
        font-family:'IBM Plex Mono',monospace;
    }

    .stTabs [aria-selected="true"]{background:var(--ink)!important;color:var(--bg)!important;}

    @media(max-width:900px){
        .case-grid,.data-grid,.case-kpis{grid-template-columns:1fr}
        .hero{padding:26px;min-height:auto}
        .hero-title{font-size:52px}
        .pitch{padding:18px}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_data():
    return pd.read_csv(ROOT / "data" / "processed" / "sample_brazil_players.csv")


def load_team_strength():
    return pd.read_csv(ROOT / "data" / "reference" / "team_strength_index.csv")


def metric_card(label, value, note):
    st.markdown(
        f"<div class='metric-card'><span>{label}</span><strong>{value}</strong><div class='muted'>{note}</div></div>",
        unsafe_allow_html=True,
    )


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


raw_df = load_data()
raw_df = raw_df[raw_df["minutes"] >= MIN_MINUTES].copy()
df = assign_squad_role(calculate_scores(add_features(raw_df)))
xi = select_best_xi(df)
reserves = select_reserves(df, xi)
team_strength = load_team_strength()
brazil_strength = float(team_strength.loc[team_strength["team"] == "Brazil", "strength_index"].iloc[0])
contenders = compare_title_contenders(team_strength, simulations=SIMULATIONS, top_n=10)

avg_score = round(xi["score_final"].mean(), 1)
total_minutes = int(xi["minutes"].sum())
total_goals = int(xi["goals"].sum())
total_assists = int(xi["assists"].sum())

st.markdown(
    """
    <div class='hero'>
      <div>
        <div class='eyebrow'>Football analytics / Decision intelligence / World Cup 2026</div>
        <h1 class='hero-title'>Brazil squad logic, <em>made readable.</em></h1>
        <div class='hero-text'>
          A polished portfolio report explaining Brazil's statistical XI, the data strategy behind the model and the Seleção's comparative title outlook. The interface is fixed as a published analytical case: no manual strength tuning, no playground controls, only model output, assumptions and decisions.
        </div>
      </div>
      <div style='margin-top:28px'>
        <span class='chip'>Python</span><span class='chip'>Streamlit</span><span class='chip'>PostgreSQL-ready</span><span class='chip'>Monte Carlo</span><span class='chip'>SportsDataverse candidate</span><span class='chip'>Squad scoring</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    metric_card("Score médio do XI", avg_score, "Média dos titulares sugeridos")
with m2:
    metric_card("Minutos do XI", f"{total_minutes:,}".replace(",", "."), "Ritmo competitivo agregado")
with m3:
    metric_card("Gols do XI", total_goals, "Produção recente da base")
with m4:
    metric_card("Força Brasil", f"{brazil_strength:.0f}", "Valor fixo no dataset do modelo")

report_tab, sources_tab, xi_tab, contenders_tab, method_tab, api_tab, tables_tab = st.tabs([
    "Full report",
    "Data sources",
    "XI + Raciocínio",
    "Top 10 favoritas",
    "Método estatístico",
    "Database/API",
    "Tabelas",
])

with report_tab:
    st.markdown(
        """
        <div class='case-hero'>
          <div class='eyebrow'>Full model report / Portfolio case</div>
          <div class='case-title'>A transparent decision model for Brazil's squad and World Cup outlook.</div>
          <div class='case-lead'>
            This report documents why each layer exists: the player data, the tactical role mapping, the score construction,
            the fixed national-team strength index and the comparison against the most likely title contenders.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='case-kpis'>
          <div class='case-kpi'><span>Decision</span><strong>Best XI</strong></div>
          <div class='case-kpi'><span>Method</span><strong>Role scoring</strong></div>
          <div class='case-kpi'><span>Forecast</span><strong>Top 10 title race</strong></div>
          <div class='case-kpi'><span>Database</span><strong>PostgreSQL-ready</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Problem framing")
    st.markdown(
        """
        The project treats national-team selection as a decision-intelligence problem. The question is not simply who has the biggest reputation or who scored the most goals. The real decision is: **which player provides the strongest statistical evidence for a specific tactical role, under a transparent set of assumptions?**

        This matters because a football team is constrained by structure. A forward, a fullback and a defensive midfielder do not create value in the same way. The model avoids a single flat ranking and instead selects players by tactical function.
        """
    )

    st.markdown("### Why these data fields are used")
    st.markdown(
        """
        The current MVP uses fields that are broadly available across football APIs and public datasets: minutes, appearances, goals, assists, rating, league, club, passes, duels, tackles, interceptions and cards.

        These variables were chosen for three reasons: they are available across multiple sources; they can be normalized by 90 minutes; and they map directly to football roles. Attackers need offensive production, midfielders need mixed contribution, defenders need reliability, and goalkeepers need rhythm and rating until richer keeper metrics are added.
        """
    )

    st.markdown("### How each decision is processed")
    decision_table = pd.DataFrame(
        [
            ["Minutagem", "Filters low-sample players", "Players below 300 minutes are excluded from the published report."],
            ["League weight", "Controls for competition level", "Production in stronger leagues receives more model confidence."],
            ["Per-90 metrics", "Makes players comparable", "Goals, assists, tackles and key actions are scaled to 90 minutes."],
            ["Role mapping", "Prevents unfair comparisons", "Players compete inside GK, RB, CB, LB, DM/CM, RW, AM/SS, LW or ST."],
            ["Score final", "Creates one decision index", "Normalized features are combined into a 0-100 score."],
            ["Direct competitor", "Explains the selection", "Each starter is compared against the next-best player in the same function."],
            ["Team strength", "Feeds title forecast", "Brazil's strength index is fixed in the dataset, not manually adjusted by the viewer."],
        ],
        columns=["Decision layer", "Purpose", "How it is applied"],
    )
    st.dataframe(decision_table, use_container_width=True, hide_index=True)

    st.markdown("### Current limitations and roadmap")
    roadmap = pd.DataFrame(
        [
            ["v1", "Current portfolio MVP", "CSV sample, role score, XI explanation, top-10 contender comparison."],
            ["v2", "Database version", "PostgreSQL schema, ingestion scripts, raw/processed tables and reproducible ETL."],
            ["v3", "Better football data", "Integrate API-Football and evaluate SportsDataverse/worldfootballR as complementary source."],
            ["v4", "Advanced metrics", "Add xG, xA, progressive actions, pressures, shot quality and goalkeeper metrics."],
            ["v5", "Tournament simulator", "Use official groups, bracket path, Elo/FIFA ranking, injuries and squad availability."],
        ],
        columns=["Version", "Focus", "What changes"],
    )
    st.dataframe(roadmap, use_container_width=True, hide_index=True)

with sources_tab:
    st.markdown("### Data-source strategy")
    st.markdown(
        """
        The MVP ships with a sample CSV to keep the dashboard reproducible, but the production design should use layered data ingestion. SportsDataverse is a strong candidate for the open-source layer because its ecosystem already organizes sports data into clean, reproducible packages.
        """
    )

    source_cards = [
        ("API-Football / API-Sports", "Primary ingestion layer", "Broad football coverage for players, teams, competitions, fixtures and season statistics. Best suited for automated ETL into PostgreSQL or BigQuery."),
        ("SportsDataverse", "Open-source sports ecosystem", "Originated from reproducible sports analytics work and offers packages across football, basketball, baseball, hockey, soccer, odds and visualization."),
        ("worldfootballR", "Soccer data candidate", "Designed to extract world football results and player statistics from FBref, Transfermarkt and Understat; useful for season stats, valuations and match data."),
        ("ggshakeR", "Soccer analysis layer", "Works with publicly available soccer data, including FBref, StatsBomb and Understat, and can support deeper visualization or analysis workflows."),
        ("sportyR / soccerAnimate", "Visualization layer", "Useful for scaled playing surfaces and 2D soccer tracking animations if the project evolves beyond tabular dashboarding."),
        ("oddsapiR", "Market signal layer", "Can provide sports odds through The Odds API, useful later for comparing model probabilities with market-implied expectations."),
    ]

    st.markdown("<div class='data-grid'>", unsafe_allow_html=True)
    for title, role, description in source_cards:
        st.markdown(
            f"""
            <div class='data-card'>
              <span>{role}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Recommended source architecture")
    source_arch = pd.DataFrame(
        [
            ["Raw ingestion", "API-Football + worldfootballR", "Collect season stats, match data, club context and player identity fields."],
            ["Reference enrichment", "Transfermarkt via worldfootballR", "Add market value, club movement and roster context."],
            ["Advanced performance", "FBref / Understat via worldfootballR", "Add xG, xA and attacking/defensive rate metrics where available."],
            ["Model benchmark", "Elo/FIFA/odds layer", "Replace manual strength index with external team-strength signals."],
            ["Presentation", "Streamlit + portfolio styling", "Publish a readable case with method, assumptions, output and limitations."],
        ],
        columns=["Layer", "Candidate source", "Purpose"],
    )
    st.dataframe(source_arch, use_container_width=True, hide_index=True)

with xi_tab:
    st.markdown("<div class='section-title'>XI estatístico</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>Nomes, função, métrica-chave e justificativa. O modelo compara jogadores dentro da mesma função tática, não em um ranking bruto único.</div>", unsafe_allow_html=True)
    render_tactical_board(xi)
    st.markdown("### Por que esses 11 foram escolhidos")
    for _, row in xi.sort_values("squad_position").iterrows():
        st.markdown(
            f"<div class='rationale-card'><div class='reason-title'>{row['player_name']} — {ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div><div class='reason-text'>{explain_choice(row, df)}</div></div>",
            unsafe_allow_html=True,
        )

with contenders_tab:
    st.markdown("<div class='section-title'>Top 10 favoritas</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-copy'>A comparação usa o índice de força das seleções e uma simulação Monte Carlo simplificada. A chance de título é normalizada entre as 10 maiores forças da base para leitura comparativa.</div>", unsafe_allow_html=True)
    fig = px.bar(
        contenders,
        x="title_probability_pct",
        y="team",
        orientation="h",
        text="title_probability_pct",
        hover_data=["strength_index", "final_probability_pct", "semifinal_probability_pct"],
        labels={"title_probability_pct": "Chance de título (%)", "team": "Seleção"},
    )
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(
        height=540,
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f7f5ef",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        contenders[["team", "strength_index", "title_probability_pct", "final_probability_pct", "semifinal_probability_pct"]],
        use_container_width=True,
        hide_index=True,
    )

with method_tab:
    st.markdown("<div class='section-title'>Método estatístico</div>", unsafe_allow_html=True)
    st.markdown(
        """
        O modelo trabalha em duas camadas. Primeiro, calcula a força individual dos jogadores por função. Depois, usa a força agregada do Brasil para comparar a Seleção com outras candidatas ao título.

        A escolha do XI segue esta lógica: filtra jogadores com minutagem mínima, cria métricas por 90 minutos, aplica peso por liga, normaliza tudo em escala comparável, calcula score final e seleciona o melhor jogador dentro de cada função do 4-2-3-1.
        """
    )
    st.code(
        """Score Final =
0.30 * performance por posição
+ 0.20 * minutagem
+ 0.15 * nível da liga
+ 0.15 * forma recente
+ 0.10 * uso/teste na Seleção
+ 0.10 * encaixe tático""",
        language="text",
    )
    st.markdown("#### Ranking por função")
    rr = role_ranking(df)
    st.dataframe(rr, use_container_width=True, hide_index=True)

with api_tab:
    st.markdown("<div class='section-title'>Database/API documentation</div>", unsafe_allow_html=True)
    schema = pd.DataFrame(
        [
            ["players", "Dimensão", "Cadastro dos jogadores brasileiros elegíveis"],
            ["teams", "Dimensão", "Clubes, país e liga principal"],
            ["leagues", "Dimensão", "Peso competitivo de cada liga"],
            ["player_season_stats", "Fato", "Minutos, gols, assists, passes, duelos, cartões e rating"],
            ["national_team_tests", "Fato", "Jogos/testes da Seleção, formação e função usada"],
            ["player_scores", "Modelo", "Scores calculados por função e temporada"],
            ["team_strength_index", "Modelo", "Força estimada das seleções para simulação da Copa"],
        ],
        columns=["Tabela", "Tipo", "Descrição"],
    )
    st.dataframe(schema, use_container_width=True, hide_index=True)
    st.markdown("**Estrutura recomendada:** MVP em CSV + pandas; versão técnica em PostgreSQL; versão cloud em BigQuery + dbt/SQL.")
    st.markdown("#### Base carregada")
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

with tables_tab:
    st.markdown("<div class='section-title'>Auditoria do elenco</div>", unsafe_allow_html=True)
    st.markdown("#### Titulares")
    st.dataframe(compact_xi(xi), use_container_width=True, hide_index=True)
    st.markdown("#### Reservas")
    st.dataframe(
        reserves[["player_name", "team", "league", "position", "score_final", "minutes", "goals", "assists", "rating"]],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("#### Produção ofensiva x minutagem")
    fig_scatter = px.scatter(
        df,
        x="minutes",
        y="goal_contributions_p90",
        size="score_final",
        hover_name="player_name",
        color="league_weight",
        labels={
            "minutes": "Minutos",
            "goal_contributions_p90": "Gols + assistências por 90",
            "league_weight": "Peso da liga",
        },
    )
    fig_scatter.update_layout(
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f7f5ef",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
