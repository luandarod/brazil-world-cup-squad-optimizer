import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.feature_engineering import add_features
from src.scoring_model import calculate_scores
from src.squad_optimizer import select_best_xi, select_reserves
from src.tournament_predictor import simulate_brazil_campaign, simulate_group_stage

st.set_page_config(
    page_title="Brazil World Cup Data Lab",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    .main {background-color: #F7F8FA;}
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .hero-card {
        background: linear-gradient(135deg, #071C33 0%, #123B63 48%, #0E7C66 100%);
        padding: 30px;
        border-radius: 26px;
        color: white;
        box-shadow: 0 18px 42px rgba(11, 31, 58, 0.28);
        margin-bottom: 22px;
    }
    .hero-title {font-size: 38px; font-weight: 850; margin-bottom: 6px;}
    .hero-subtitle {font-size: 16px; opacity: 0.90; max-width: 980px;}
    .section-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
        margin-bottom: 18px;
    }
    .small-label {font-size: 12px; color: #6B7280; text-transform: uppercase; letter-spacing: .06em; font-weight: 750;}
    .big-number {font-size: 34px; font-weight: 850; color: #111827; margin-top: 2px;}
    .muted {font-size: 13px; color: #6B7280;}
    .pipeline-step {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 14px;
        min-height: 116px;
    }
    .pitch {
        background: radial-gradient(circle at center, rgba(255,255,255,0.13) 0%, rgba(255,255,255,0.05) 18%, transparent 19%), linear-gradient(180deg,#0B6B3A,#064D2E);
        border: 2px solid rgba(255,255,255,0.55);
        border-radius: 28px;
        padding: 22px;
        box-shadow: 0 16px 36px rgba(6, 77, 46, 0.22);
        margin-bottom: 18px;
    }
    .player-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 13px 12px;
        margin: 6px 0;
        text-align: center;
        box-shadow: 0 6px 18px rgba(0,0,0,0.10);
        min-height: 132px;
    }
    .player-role {font-size: 11px; color: #0F766E; font-weight: 850; text-transform: uppercase; letter-spacing: .05em;}
    .player-name {font-size: 20px; color: #111827; font-weight: 900; margin-top: 4px;}
    .player-team {font-size: 12px; color: #4B5563; margin-top: 2px;}
    .player-score {font-size: 14px; color: #111827; font-weight: 800; margin-top: 8px;}
    .player-reason {font-size: 12px; color: #374151; margin-top: 4px; line-height: 1.25;}
    .rationale-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(15,23,42,0.05);
    }
    .reason-title {font-size: 16px; font-weight: 850; color: #111827; margin-bottom: 4px;}
    .reason-text {font-size: 13px; color: #374151; line-height: 1.45;}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_data(uploaded_file):
    sample_path = ROOT / "data" / "processed" / "sample_brazil_players.csv"
    if uploaded_file:
        return pd.read_csv(uploaded_file)
    return pd.read_csv(sample_path)


def load_team_strength():
    return pd.read_csv(ROOT / "data" / "reference" / "team_strength_index.csv")


def render_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="section-card">
            <div class="small-label">{label}</div>
            <div class="big-number">{value}</div>
            <div class="muted">{note}</div>
        </div>
        """,
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
        return f"{row['duel_win_rate']:.0%} duelos vencidos e {row['tackles_p90']:.2f} desarmes/90"
    return f"{int(row['minutes'])} minutos e rating {row['rating']:.2f}"


def direct_competitor(row, df):
    role_df = df[df["squad_position"] == row["squad_position"]].sort_values("score_final", ascending=False)
    role_df = role_df[role_df["player_name"] != row["player_name"]]
    if role_df.empty:
        return "sem concorrente direto na base"
    comp = role_df.iloc[0]
    diff = row["score_final"] - comp["score_final"]
    return f"à frente de {comp['player_name']} por {diff:.1f} pts de score"


def explain_choice(row, df):
    metric = best_metric(row)
    competitor = direct_competitor(row, df)
    return (
        f"Escolhido para {ROLE_LABELS.get(row['squad_position'], row['squad_position'])} porque lidera ou fica no topo da função pelo score final "
        f"({row['score_final']:.1f}). O modelo valorizou {int(row['minutes'])} minutos, peso da liga {row['league_weight']:.2f}, "
        f"rating {row['rating']:.2f} e {metric}. Comparação direta: {competitor}."
    )


def player_card(row, df):
    reason = best_metric(row)
    return f"""
    <div class="player-card">
        <div class="player-role">{ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div>
        <div class="player-name">{row['player_name']}</div>
        <div class="player-team">{row['team']} · {row['league']}</div>
        <div class="player-score">Score {row['score_final']:.1f} · {int(row['minutes'])} min</div>
        <div class="player-reason">{reason}</div>
    </div>
    """


def render_tactical_board(xi, df):
    xi = xi.copy()
    by_role = {role: xi[xi["squad_position"] == role].to_dict("records") for role in xi["squad_position"].unique()}
    used_index = {role: 0 for role in by_role}

    st.markdown("### XI estatístico — 4-2-3-1")
    st.caption("Os nomes aparecem diretamente no esquema. Cada card mostra função, clube, score e a métrica que mais pesou dentro daquela posição.")
    st.markdown("<div class='pitch'>", unsafe_allow_html=True)
    for line in TACTICAL_LINES:
        cols = st.columns(len(line))
        for i, role in enumerate(line):
            with cols[i]:
                candidates = by_role.get(role, [])
                idx = used_index.get(role, 0)
                if idx < len(candidates):
                    st.markdown(player_card(candidates[idx], df), unsafe_allow_html=True)
                    used_index[role] = idx + 1
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
    <div class="hero-card">
        <div class="hero-title">Brazil World Cup Data Lab</div>
        <div class="hero-subtitle">
            Dashboard para explicar a escolha estatística do XI do Brasil, visualizar a base de dados
            e simular até onde a Seleção pode chegar na Copa de 2026.
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
df = calculate_scores(add_features(raw_df))

# Mapeia função tática para todo o dataframe para permitir comparação por função.
from src.squad_optimizer import assign_squad_role

df = assign_squad_role(df)
xi = select_best_xi(df)
reserves = select_reserves(df, xi)
team_strength = load_team_strength()

avg_score = round(xi["score_final"].mean(), 1)
total_minutes = int(xi["minutes"].sum())
total_goals = int(xi["goals"].sum())
total_assists = int(xi["assists"].sum())

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_card("Score médio do XI", avg_score, "Média dos titulares sugeridos")
with col2:
    render_card("Minutos do XI", f"{total_minutes:,}".replace(",", "."), "Ritmo competitivo agregado")
with col3:
    render_card("Gols do XI", total_goals, "Produção recente da base")
with col4:
    render_card("Assistências do XI", total_assists, "Criação direta de gols")

xi_tab, reasoning_tab, api_tab, prediction_tab, squad_tab = st.tabs([
    "XI + Raciocínio",
    "Método estatístico",
    "Database/API",
    "Previsão Copa 2026",
    "Tabelas do elenco",
])

with xi_tab:
    render_tactical_board(xi, df)

    st.markdown("### Por que esses 11 foram escolhidos")
    for _, row in xi.sort_values("squad_position").iterrows():
        st.markdown(
            f"""
            <div class="rationale-card">
                <div class="reason-title">{row['player_name']} — {ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div>
                <div class="reason-text">{explain_choice(row, df)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with reasoning_tab:
    st.markdown("### Como o modelo escolhe estatisticamente")
    st.markdown(
        """
        A escolha não é feita pelo nome do jogador. O modelo primeiro separa o elenco por função tática e só depois compara jogadores dentro da mesma função.

        Isso evita uma distorção comum: um atacante quase sempre terá mais gols que um lateral, mas isso não significa que ele sirva para ocupar uma vaga defensiva. Por isso, cada jogador concorre contra quem disputa a mesma função.
        """
    )

    st.markdown("#### Etapas do raciocínio")
    steps = pd.DataFrame([
        ["1", "Filtragem", "Remove jogadores abaixo da minutagem mínima definida no menu lateral."],
        ["2", "Normalização", "Transforma métricas diferentes em escala comparável, como minutos, rating, gols/90 e duelos."],
        ["3", "Peso competitivo", "Aplica peso de liga. Premier League, LaLiga e Serie A têm maior peso que ligas menos fortes."],
        ["4", "Score final", "Combina performance, minutagem, peso da liga, forma, uso na Seleção e encaixe tático."],
        ["5", "Escolha por função", "Seleciona o maior score em cada papel do 4-2-3-1: GK, RB, CB, LB, DM/CM, RW, AM/SS, LW e ST."],
        ["6", "Banco", "Depois dos titulares, os melhores scores restantes viram reservas sugeridos."],
    ], columns=["Ordem", "Etapa", "O que acontece"])
    st.dataframe(steps, use_container_width=True, hide_index=True)

    st.markdown("#### Fórmula de score")
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

    st.markdown("#### Ranking por função, não só ranking geral")
    rr = role_ranking(df)
    st.dataframe(rr, use_container_width=True, hide_index=True)

    fig_role = px.bar(
        rr,
        x="score",
        y="jogador",
        color="função",
        orientation="h",
        hover_data=["clube", "liga", "minutos", "métrica-chave"],
        labels={"score": "Score", "jogador": "Jogador"},
    )
    fig_role.update_layout(height=720, yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_role, use_container_width=True)

with api_tab:
    st.markdown("### Database/API view")
    st.markdown(
        "Esta aba mostra como o projeto deve ser lido como produto de dados: quais tabelas entram, o que cada uma armazena e como isso vira uma base analítica para previsão e escolha de elenco."
    )

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown("#### Modelo de dados recomendado")
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

    with c2:
        st.markdown("#### Stack sugerida")
        st.markdown(
            """
            <div class="section-card">
                <b>MVP</b><br>CSV + pandas + Streamlit<br><br>
                <b>Portfólio técnico</b><br>PostgreSQL + SQL + pandas<br><br>
                <b>Versão cloud</b><br>BigQuery + dbt + Looker/Power BI
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### Pipeline de dados")
    pipe = pd.DataFrame([
        ["API-Football / CSV", "Entrada bruta", "dados de jogadores, clubes, ligas e temporadas"],
        ["data/raw", "Landing zone", "armazena resposta bruta da API ou CSV original"],
        ["data/processed", "Camada tratada", "base limpa com colunas padronizadas"],
        ["feature_engineering.py", "Transformação", "métricas por 90 minutos, peso de liga e disciplina"],
        ["scoring_model.py", "Modelo", "score final por jogador"],
        ["squad_optimizer.py", "Decisão", "seleção por função tática"],
    ], columns=["Camada", "Tipo", "Descrição"])
    st.dataframe(pipe, use_container_width=True, hide_index=True)

    st.markdown("#### Base carregada no app")
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

with prediction_tab:
    st.markdown("### Previsão estatística da campanha do Brasil")
    st.markdown(
        "A simulação usa um índice de força para o Brasil e adversários médios por fase. É uma primeira camada explicável, não uma previsão definitiva. Quando os grupos e chave oficial estiverem definidos, o modelo pode ser substituído por simulação completa jogo a jogo."
    )

    campaign = simulate_brazil_campaign(brazil_strength=brazil_strength, simulations=simulations)
    campaign["probability_pct"] = (campaign["probability"] * 100).round(1)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        fig_campaign = px.bar(
            campaign,
            x="stage",
            y="probability_pct",
            text="probability_pct",
            labels={"stage": "Fase", "probability_pct": "Probabilidade (%)"},
        )
        fig_campaign.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_campaign.update_layout(height=470, margin=dict(l=10, r=10, t=20, b=10), yaxis_range=[0, 105])
        st.plotly_chart(fig_campaign, use_container_width=True)

    with c2:
        champion_prob = campaign.loc[campaign["stage"] == "Champion", "probability_pct"].iloc[0]
        final_prob = campaign.loc[campaign["stage"] == "Final", "probability_pct"].iloc[0]
        semifinal_prob = campaign.loc[campaign["stage"] == "Semifinal", "probability_pct"].iloc[0]
        render_card("Chance de título", f"{champion_prob}%", "Monte Carlo simplificado")
        render_card("Chance de final", f"{final_prob}%", "Probabilidade de alcançar a decisão")
        render_card("Chance de semifinal", f"{semifinal_prob}%", "Probabilidade de chegar entre os quatro")

    st.markdown("#### Simular grupo hipotético")
    selected_opponents = st.multiselect(
        "Escolha 3 adversários para um grupo hipotético",
        options=[t for t in team_strength["team"].tolist() if t != "Brazil"],
        default=["Mexico", "Japan", "Morocco"],
        max_selections=3,
    )
    if len(selected_opponents) == 3:
        group_df = team_strength[team_strength["team"].isin(["Brazil"] + selected_opponents)].copy()
        group_df.loc[group_df["team"] == "Brazil", "strength_index"] = brazil_strength
        group_result = simulate_group_stage(group_df, target_team="Brazil", simulations=simulations)
        group_result["probability_pct"] = (group_result["probability"] * 100).round(1)

        gc1, gc2 = st.columns([1, 1])
        with gc1:
            st.dataframe(group_df, use_container_width=True, hide_index=True)
        with gc2:
            fig_group = px.bar(
                group_result,
                x="position",
                y="probability_pct",
                text="probability_pct",
                labels={"position": "Posição no grupo", "probability_pct": "Probabilidade (%)"},
            )
            fig_group.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_group.update_layout(height=330, yaxis_range=[0, 105])
            st.plotly_chart(fig_group, use_container_width=True)
    else:
        st.info("Escolha exatamente 3 adversários para simular um grupo.")

with squad_tab:
    st.markdown("### Tabelas do elenco")
    st.markdown("Aqui ficam as tabelas completas para auditoria do resultado.")

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
    fig_scatter.update_layout(height=480, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_scatter, use_container_width=True)
