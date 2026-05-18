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
from src.tournament_predictor import simulate_brazil_campaign, simulate_group_stage, match_probabilities

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

st.markdown(
    """
    <style>
    .main {background-color: #F7F8FA;}
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .hero-card {
        background: linear-gradient(135deg, #0B1F3A 0%, #123B63 45%, #0E7C66 100%);
        padding: 30px;
        border-radius: 26px;
        color: white;
        box-shadow: 0 18px 42px rgba(11, 31, 58, 0.28);
        margin-bottom: 22px;
    }
    .hero-title {font-size: 36px; font-weight: 800; margin-bottom: 6px;}
    .hero-subtitle {font-size: 16px; opacity: 0.88; max-width: 920px;}
    .section-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
        margin-bottom: 18px;
    }
    .small-label {font-size: 12px; color: #6B7280; text-transform: uppercase; letter-spacing: .06em; font-weight: 700;}
    .big-number {font-size: 34px; font-weight: 800; color: #111827; margin-top: 2px;}
    .muted {font-size: 13px; color: #6B7280;}
    .pipeline-step {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 14px;
        height: 116px;
    }
    .player-pill {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 10px 12px;
        margin: 4px 0;
    }
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
    path = ROOT / "data" / "reference" / "team_strength_index.csv"
    return pd.read_csv(path)


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
    xi = xi.copy()
    xi["função"] = xi["squad_position"].map(ROLE_LABELS)
    return xi[["função", "player_name", "team", "league", "score_final", "minutes", "goals", "assists"]]


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">Brazil World Cup Data Lab</div>
        <div class="hero-subtitle">
            Dashboard para visualizar a base de jogadores brasileiros, entender o processamento dos dados
            e simular até onde o Brasil pode chegar na Copa de 2026 com base em força estatística do elenco.
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

api_tab, model_tab, prediction_tab, squad_tab = st.tabs([
    "Database/API",
    "Processamento",
    "Previsão Copa 2026",
    "Elenco sugerido",
])

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

    st.markdown("#### Base carregada no app")
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

with model_tab:
    st.markdown("### Pipeline de processamento")
    steps = [
        ("1. Ingestão", "API-Football ou CSV manual com jogadores brasileiros."),
        ("2. Limpeza", "Padroniza nomes, converte numéricos e remove registros sem minutos."),
        ("3. Features", "Cria métricas por 90 minutos e peso de liga."),
        ("4. Score", "Normaliza métricas e calcula score final de 0 a 100."),
        ("5. Seleção", "Escolhe titulares por função no 4-2-3-1."),
        ("6. Previsão", "Usa strength index e Monte Carlo para campanha na Copa."),
    ]
    cols = st.columns(3)
    for i, (title, desc) in enumerate(steps):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="pipeline-step">
                    <b>{title}</b><br>
                    <span class="muted">{desc}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("#### Fórmula do score")
    st.code(
        """Score Final =
0.30 * performance por posição
+ 0.20 * minutagem
+ 0.15 * nível da liga
+ 0.15 * forma recente
+ 0.10 * uso na Seleção
+ 0.10 * encaixe tático""",
        language="text",
    )

    st.markdown("#### Ranking geral")
    fig = px.bar(
        df.sort_values("score_final", ascending=False).head(15),
        x="score_final",
        y="player_name",
        orientation="h",
        hover_data=["team", "league", "minutes", "goals", "assists"],
        labels={"score_final": "Score", "player_name": "Jogador"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

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
        render_card("Chance de título", f"{champion_prob}%", "Simulação Monte Carlo simplificada")
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
    st.markdown("### Elenco sugerido pelo modelo")
    st.markdown("A escalação deixa de ser o foco visual principal, mas continua disponível como saída do modelo.")

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
