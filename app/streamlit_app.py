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

st.title("Brazil World Cup Squad Optimizer")
st.caption("Modelo de apoio para escolha de elenco e time titular com base em dados.")

sample_path = ROOT / "data" / "processed" / "sample_brazil_players.csv"

uploaded = st.file_uploader("Envie uma base CSV de jogadores ou use o exemplo", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
else:
    df = pd.read_csv(sample_path)

df = add_features(df)
df = calculate_scores(df)

st.subheader("Ranking geral de jogadores")
st.dataframe(
    df[["player_name", "team", "league", "position", "minutes", "goals", "assists", "rating", "score_final"]]
    .sort_values("score_final", ascending=False),
    use_container_width=True
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 15 por score")
    fig = px.bar(
        df.sort_values("score_final", ascending=False).head(15),
        x="score_final",
        y="player_name",
        orientation="h",
        hover_data=["team", "league", "minutes", "goals", "assists"]
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Gols + assistências por 90")
    fig2 = px.scatter(
        df,
        x="minutes",
        y="goal_contributions_p90",
        size="score_final",
        hover_name="player_name",
        color="league_weight"
    )
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Time titular sugerido")
xi = select_best_xi(df)
st.dataframe(
    xi[["squad_position", "player_name", "team", "league", "score_final", "minutes", "goals", "assists"]],
    use_container_width=True
)

st.subheader("Reservas sugeridos")
reserves = select_reserves(df, xi)
st.dataframe(
    reserves[["player_name", "team", "league", "position", "score_final", "minutes", "goals", "assists"]],
    use_container_width=True
)

st.info(
    "O modelo é ajustável. Os pesos de score podem ser alterados em src/scoring_model.py "
    "e os pesos por liga em src/feature_engineering.py."
)
