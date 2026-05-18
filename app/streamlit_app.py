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

st.set_page_config(page_title="Brazil World Cup Squad Optimizer", layout="wide")

ROLE_ORDER = ["GK", "LB", "CB", "RB", "DM_CM", "LW", "AM_SS", "RW", "ST"]
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


def load_data(uploaded_file):
    sample_path = ROOT / "data" / "processed" / "sample_brazil_players.csv"
    if uploaded_file:
        return pd.read_csv(uploaded_file)
    return pd.read_csv(sample_path)


def player_card(row):
    return f"""
    <div style="
        border:1px solid #E5E7EB;
        border-radius:16px;
        padding:14px;
        margin:6px;
        background:#FFFFFF;
        box-shadow:0 1px 4px rgba(0,0,0,0.06);
        text-align:center;
        min-height:112px;">
        <div style="font-size:12px;color:#6B7280;font-weight:600;">{ROLE_LABELS.get(row['squad_position'], row['squad_position'])}</div>
        <div style="font-size:18px;font-weight:700;margin-top:4px;">{row['player_name']}</div>
        <div style="font-size:12px;color:#4B5563;">{row['team']} · {row['league']}</div>
        <div style="font-size:13px;margin-top:6px;">
            <b>Score:</b> {row['score_final']} · <b>Min:</b> {int(row['minutes'])}
        </div>
        <div style="font-size:12px;color:#374151;">
            {int(row['goals'])} gols · {int(row['assists'])} assist.
        </div>
    </div>
    """


def render_pitch(xi):
    xi = xi.copy()
    by_role = {role: xi[xi["squad_position"] == role].to_dict("records") for role in xi["squad_position"].unique()}

    st.markdown("### Escalação visual — 4-2-3-1")
    st.caption("A formação é montada escolhendo o maior score dentro de cada função. O banco usa os melhores jogadores restantes.")

    pitch_style = """
    <div style="
        background:linear-gradient(180deg,#0B6B3A,#0A5C34);
        border-radius:24px;
        padding:22px;
        border:2px solid rgba(255,255,255,0.35);
        box-shadow:0 8px 26px rgba(0,0,0,0.18);
        margin-bottom:20px;">
    """
    st.markdown(pitch_style, unsafe_allow_html=True)

    lines = [
        ["ST"],
        ["LW", "AM_SS", "RW"],
        ["DM_CM", "DM_CM"],
        ["LB", "CB", "CB", "RB"],
        ["GK"],
    ]

    used_index = {role: 0 for role in by_role}
    for line in lines:
        cols = st.columns(len(line))
        for i, role in enumerate(line):
            candidates = by_role.get(role, [])
            idx = used_index.get(role, 0)
            with cols[i]:
                if idx < len(candidates):
                    st.markdown(player_card(candidates[idx]), unsafe_allow_html=True)
                    used_index[role] = idx + 1
                else:
                    st.markdown(
                        f"<div style='border:1px dashed #D1D5DB;border-radius:16px;padding:16px;text-align:center;background:#F9FAFB;'>Sem jogador para {role}</div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("</div>", unsafe_allow_html=True)


st.title("Brazil World Cup Squad Optimizer")
st.caption("Modelo de apoio para escolha de elenco e time titular com base em dados, função tática e nível competitivo.")

uploaded = st.sidebar.file_uploader("Base CSV de jogadores", type=["csv"])
formation = st.sidebar.selectbox("Formação", ["4-2-3-1"], index=0)
min_minutes = st.sidebar.slider("Minutagem mínima para análise", min_value=0, max_value=3000, value=300, step=100)

raw_df = load_data(uploaded)
raw_df = raw_df[raw_df["minutes"] >= min_minutes].copy()

df = add_features(raw_df)
df = calculate_scores(df)
xi = select_best_xi(df)
reserves = select_reserves(df, xi)

avg_score = round(xi["score_final"].mean(), 1)
total_minutes = int(xi["minutes"].sum())
total_goals = int(xi["goals"].sum())
total_assists = int(xi["assists"].sum())

st.markdown("---")
metric_cols = st.columns(4)
metric_cols[0].metric("Score médio do XI", avg_score)
metric_cols[1].metric("Minutos somados", f"{total_minutes:,}".replace(",", "."))
metric_cols[2].metric("Gols do XI", total_goals)
metric_cols[3].metric("Assistências do XI", total_assists)

main_tab, method_tab, ranking_tab, data_tab = st.tabs([
    "Visão executiva",
    "Método de escolha",
    "Ranking e comparação",
    "Database e processamento",
])

with main_tab:
    render_pitch(xi)

    st.subheader("Titulares escolhidos")
    display_xi = xi[["squad_position", "player_name", "team", "league", "score_final", "minutes", "goals", "assists", "rating"]].copy()
    display_xi["função"] = display_xi["squad_position"].map(ROLE_LABELS)
    st.dataframe(
        display_xi[["função", "player_name", "team", "league", "score_final", "minutes", "goals", "assists", "rating"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Banco sugerido")
    st.dataframe(
        reserves[["player_name", "team", "league", "position", "score_final", "minutes", "goals", "assists", "rating"]],
        use_container_width=True,
        hide_index=True,
    )

with method_tab:
    st.subheader("Como o modelo escolhe o time")
    st.markdown(
        """
        O modelo não escolhe simplesmente os maiores nomes. Ele seleciona jogadores por função dentro da formação.

        A lógica atual é:

        1. carregar a base de jogadores;
        2. criar métricas comparáveis, como gols por 90, assistências por 90, passes-chave por 90 e duelos vencidos;
        3. aplicar peso pelo nível da liga;
        4. normalizar as métricas para uma escala comum;
        5. penalizar baixa minutagem e excesso de cartões;
        6. mapear cada jogador para uma função tática;
        7. escolher o maior score dentro de cada função do 4-2-3-1.
        """
    )

    st.markdown("#### Fórmula simplificada")
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

    st.markdown("#### Por que separar por função?")
    st.markdown(
        "Um atacante pode ter score maior que um lateral, mas isso não significa que ele deve ocupar uma vaga defensiva. Por isso, o modelo primeiro classifica jogadores por papel tático e depois escolhe os melhores dentro de cada papel."
    )

    st.markdown("#### Limitações atuais")
    st.markdown(
        """
        - A base de exemplo ainda não tem xG, xA, pressão, conduções progressivas ou lesões.
        - A camada de Seleção ainda é manual.
        - O peso das ligas é definido por regra de negócio e pode ser refinado com rankings Elo ou UEFA.
        - O modelo não mede química entre jogadores.
        """
    )

with ranking_tab:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 15 por score")
        fig = px.bar(
            df.sort_values("score_final", ascending=False).head(15),
            x="score_final",
            y="player_name",
            orientation="h",
            hover_data=["team", "league", "minutes", "goals", "assists"],
            labels={"score_final": "Score", "player_name": "Jogador"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Produção ofensiva x minutagem")
        fig2 = px.scatter(
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
        fig2.update_layout(height=520)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Base ranqueada")
    st.dataframe(
        df[["player_name", "team", "league", "position", "minutes", "goals", "assists", "rating", "league_weight", "score_final"]]
        .sort_values("score_final", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with data_tab:
    st.subheader("Qual database usar")
    st.markdown(
        """
        Para o MVP, CSV é suficiente. Para portfólio técnico, a melhor escolha é PostgreSQL. Para uma versão cloud, BigQuery.

        **Recomendação de evolução:**

        ```text
        MVP: CSV + pandas + Streamlit
        Portfólio técnico: PostgreSQL + pandas/SQL + Streamlit
        Cloud analytics: BigQuery + dbt/SQL + Looker/Power BI
        ```
        """
    )

    st.subheader("Tabelas recomendadas")
    schema = pd.DataFrame([
        ["players", "Cadastro do jogador", "player_id, player_name, nationality, age, preferred_position"],
        ["teams", "Cadastro dos clubes", "team_id, team_name, country, league_id"],
        ["leagues", "Peso competitivo das ligas", "league_id, league_name, country, league_weight"],
        ["player_season_stats", "Tabela fato de performance", "minutes, goals, assists, passes, duels, cards, rating"],
        ["national_team_tests", "Escalações e testes da Seleção", "date, coach, opponent, formation, player, position_used"],
        ["player_scores", "Resultado do modelo", "performance_score, minutes_score, league_score, final_score"],
    ], columns=["Tabela", "Função", "Campos principais"])
    st.dataframe(schema, use_container_width=True, hide_index=True)

    st.subheader("Pipeline de processamento")
    st.code(
        """API-Football / CSV bruto
    ↓
data/raw
    ↓
Limpeza e padronização
    ↓
data/processed
    ↓
Feature engineering por 90 minutos
    ↓
Score multicritério
    ↓
Otimização da escalação
    ↓
Streamlit / Power BI / relatório""",
        language="text",
    )

    st.subheader("Base carregada")
    st.dataframe(raw_df, use_container_width=True, hide_index=True)
