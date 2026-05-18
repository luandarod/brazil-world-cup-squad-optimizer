import pandas as pd

FORMATION_4231 = {
    "GK": 1,
    "RB": 1,
    "CB": 2,
    "LB": 1,
    "DM_CM": 2,
    "RW": 1,
    "AM_SS": 1,
    "LW": 1,
    "ST": 1,
}

POSITION_MAP = {
    "Alisson": "GK",
    "Ederson": "GK",
    "Weverton": "GK",
    "Wesley": "RB",
    "Danilo": "RB",
    "Alex Sandro": "LB",
    "Douglas Santos": "LB",
    "Gabriel Magalhães": "CB",
    "Gabriel": "CB",
    "Bremer": "CB",
    "Marquinhos": "CB",
    "Ibañez": "CB",
    "Léo Pereira": "CB",
    "Casemiro": "DM_CM",
    "Bruno Guimarães": "DM_CM",
    "Fabinho": "DM_CM",
    "Danilo Midfielder": "DM_CM",
    "Lucas Paquetá": "AM_SS",
    "Paquetá": "AM_SS",
    "Raphinha": "RW",
    "Luiz Henrique": "RW",
    "Vinícius Júnior": "LW",
    "Vini Jr": "LW",
    "Gabriel Martinelli": "LW",
    "Neymar": "AM_SS",
    "Matheus Cunha": "AM_SS",
    "Endrick": "ST",
    "Igor Thiago": "ST",
    "Rayan": "ST",
}

def assign_squad_role(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["squad_position"] = df["player_name"].map(POSITION_MAP).fillna(df.get("position_group", "UNK"))
    return df

def select_best_xi(df: pd.DataFrame, formation: dict = FORMATION_4231) -> pd.DataFrame:
    df = assign_squad_role(df)
    selected = []

    for role, n in formation.items():
        candidates = df[df["squad_position"] == role].sort_values("score_final", ascending=False)
        selected.append(candidates.head(n))

    xi = pd.concat(selected, ignore_index=True)
    return xi.sort_values("squad_position")

def select_reserves(df: pd.DataFrame, xi: pd.DataFrame, reserve_size: int = 12) -> pd.DataFrame:
    if "player_id" in df.columns and "player_id" in xi.columns:
        used_ids = set(xi["player_id"].tolist())
        reserves = df[~df["player_id"].isin(used_ids)].sort_values("score_final", ascending=False)
    else:
        used_names = set(xi["player_name"].tolist())
        reserves = df[~df["player_name"].isin(used_names)].sort_values("score_final", ascending=False)
    return reserves.head(reserve_size).reset_index(drop=True)
