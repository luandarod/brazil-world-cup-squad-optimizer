import pandas as pd
import pytest
from src.squad_optimizer import assign_squad_role, select_best_xi, select_reserves

def test_assign_squad_role() -> None:
    df = pd.DataFrame([
        {"player_name": "Alisson", "position_group": "MID"},
        {"player_name": "Neymar", "position_group": "ATT"},
        {"player_name": "Unknown Player", "position_group": "DEF"},
    ])
    res = assign_squad_role(df)
    assert res.loc[res["player_name"] == "Alisson", "squad_position"].values[0] == "GK"
    assert res.loc[res["player_name"] == "Neymar", "squad_position"].values[0] == "AM_SS"
    assert res.loc[res["player_name"] == "Unknown Player", "squad_position"].values[0] == "DEF"

def test_select_best_xi() -> None:
    # Build a roster with enough players in all positions to fill a 4-2-3-1:
    # 4-2-3-1 needs: GK: 1, RB: 1, CB: 2, LB: 1, DM_CM: 2, RW: 1, AM_SS: 1, LW: 1, ST: 1
    players = [
        {"player_name": "Alisson", "score_final": 90.0},
        {"player_name": "Ederson", "score_final": 85.0},
        
        {"player_name": "Danilo", "score_final": 80.0},
        {"player_name": "Wesley", "score_final": 75.0},
        
        {"player_name": "Gabriel Magalhães", "score_final": 88.0},
        {"player_name": "Bremer", "score_final": 84.0},
        {"player_name": "Marquinhos", "score_final": 70.0},
        
        {"player_name": "Alex Sandro", "score_final": 78.0},
        
        {"player_name": "Bruno Guimarães", "score_final": 92.0},
        {"player_name": "Casemiro", "score_final": 87.0},
        {"player_name": "Fabinho", "score_final": 72.0},
        
        {"player_name": "Raphinha", "score_final": 86.0},
        
        {"player_name": "Neymar", "score_final": 95.0},
        
        {"player_name": "Vini Jr", "score_final": 94.0},
        
        {"player_name": "Endrick", "score_final": 82.0},
        {"player_name": "Igor Thiago", "score_final": 89.0},
    ]
    df = pd.DataFrame(players)
    df = assign_squad_role(df)
    
    xi = select_best_xi(df)
    assert len(xi) == 11
    
    # Check that highest score players were selected
    # GK Alisson (90.0) over Ederson (85.0)
    assert "Alisson" in xi["player_name"].values
    assert "Ederson" not in xi["player_name"].values
    
    # ST Igor Thiago (89.0) over Endrick (82.0)
    assert "Igor Thiago" in xi["player_name"].values
    assert "Endrick" not in xi["player_name"].values
    
    # CB Gabriel Magalhães (88.0) and Bremer (84.0) over Marquinhos (70.0)
    assert "Gabriel Magalhães" in xi["player_name"].values
    assert "Bremer" in xi["player_name"].values
    assert "Marquinhos" not in xi["player_name"].values

def test_select_reserves() -> None:
    players = [
        {"player_name": "Alisson", "score_final": 90.0},
        {"player_name": "Ederson", "score_final": 85.0},
        {"player_name": "Danilo", "score_final": 80.0},
        {"player_name": "Wesley", "score_final": 75.0},
        {"player_name": "Gabriel Magalhães", "score_final": 88.0},
        {"player_name": "Bremer", "score_final": 84.0},
        {"player_name": "Marquinhos", "score_final": 70.0},
        {"player_name": "Alex Sandro", "score_final": 78.0},
        {"player_name": "Bruno Guimarães", "score_final": 92.0},
        {"player_name": "Casemiro", "score_final": 87.0},
        {"player_name": "Fabinho", "score_final": 72.0},
        {"player_name": "Raphinha", "score_final": 86.0},
        {"player_name": "Neymar", "score_final": 95.0},
        {"player_name": "Vini Jr", "score_final": 94.0},
        {"player_name": "Endrick", "score_final": 82.0},
        {"player_name": "Igor Thiago", "score_final": 89.0},
    ]
    df = pd.DataFrame(players)
    df_assigned = assign_squad_role(df)
    xi = select_best_xi(df_assigned)
    
    reserves = select_reserves(df_assigned, xi, reserve_size=3)
    assert len(reserves) == 3
    # Players in reserves must not be in XI
    for player in reserves["player_name"]:
        assert player not in xi["player_name"].values
