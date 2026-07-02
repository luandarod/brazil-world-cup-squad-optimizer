import numpy as np
import pandas as pd
import pytest
from src.scoring_model import normalize_features, calculate_scores

def test_normalize_features_basic() -> None:
    df = pd.DataFrame({
        "minutes": [500, 1000, 1500],
        "rating": [6.0, 7.0, 8.0],
    })
    res = normalize_features(df, ["minutes", "rating"])
    assert "minutes_norm" in res.columns
    assert "rating_norm" in res.columns
    # Check MinMax scaling limits
    assert res["minutes_norm"].min() == 0.0
    assert res["minutes_norm"].max() == 1.0

def test_normalize_features_edge_cases() -> None:
    df = pd.DataFrame({
        "minutes": [1000, np.nan, np.inf],
    })
    res = normalize_features(df, ["minutes"])
    assert "minutes_norm" in res.columns
    assert not res["minutes_norm"].isnull().any()
    assert (res["minutes_norm"] >= 0).all()

def test_calculate_scores_default_weights() -> None:
    df = pd.DataFrame([
        {
            "player_id": 1,
            "player_name": "Player A",
            "minutes": 2000,
            "rating": 7.5,
            "league_weight": 0.9,
            "goals_p90": 0.5,
            "assists_p90": 0.2,
            "goal_contributions_p90": 0.7,
            "key_passes_p90": 1.5,
            "tackles_p90": 2.0,
            "interceptions_p90": 1.0,
            "duel_win_rate": 0.55,
            "discipline_penalty": 1.0,
        },
        {
            "player_id": 2,
            "player_name": "Player B",
            "minutes": 500,
            "rating": 6.0,
            "league_weight": 0.7,
            "goals_p90": 0.0,
            "assists_p90": 0.0,
            "goal_contributions_p90": 0.0,
            "key_passes_p90": 0.1,
            "tackles_p90": 0.5,
            "interceptions_p90": 0.2,
            "duel_win_rate": 0.40,
            "discipline_penalty": 0.0,
        }
    ])
    scored = calculate_scores(df)
    assert "score_final" in scored.columns
    assert len(scored) == 2
    # Player A should have a much higher score than Player B due to rating, minutes, and contributions
    assert scored.loc[scored["player_name"] == "Player A", "score_final"].values[0] > scored.loc[scored["player_name"] == "Player B", "score_final"].values[0]

def test_calculate_scores_custom_weights() -> None:
    df = pd.DataFrame([
        {
            "player_name": "Goalscorer",
            "minutes": 1000,
            "rating": 7.0,
            "league_weight": 0.8,
            "goal_contributions_p90": 2.0,
            "tackles_p90": 0.0,
        },
        {
            "player_name": "Defender",
            "minutes": 1000,
            "rating": 7.0,
            "league_weight": 0.8,
            "goal_contributions_p90": 0.0,
            "tackles_p90": 5.0,
        }
    ])
    
    # Custom weight: favor goals heavily, zero on tackles
    goals_heavy = {"goal_contributions_p90": 1.0, "tackles_p90": 0.0}
    scored_goals = calculate_scores(df, weights=goals_heavy)
    g_score = scored_goals.loc[scored_goals["player_name"] == "Goalscorer", "score_final"].values[0]
    d_score = scored_goals.loc[scored_goals["player_name"] == "Defender", "score_final"].values[0]
    assert g_score > d_score
    
    # Custom weight: favor tackles heavily, zero on goals
    tackles_heavy = {"goal_contributions_p90": 0.0, "tackles_p90": 1.0}
    scored_tackles = calculate_scores(df, weights=tackles_heavy)
    g_score_t = scored_tackles.loc[scored_tackles["player_name"] == "Goalscorer", "score_final"].values[0]
    d_score_t = scored_tackles.loc[scored_tackles["player_name"] == "Defender", "score_final"].values[0]
    assert d_score_t > g_score_t
