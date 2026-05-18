import numpy as np
import pandas as pd


def win_probability(team_strength: float, opponent_strength: float, scale: float = 12.0) -> float:
    """
    Probabilidade simplificada de vitória com base na diferença de força.
    Usa uma curva logística. Empate é tratado separadamente na fase de grupos.
    """
    diff = team_strength - opponent_strength
    return 1 / (1 + np.exp(-diff / scale))


def match_probabilities(team_strength: float, opponent_strength: float) -> dict:
    """
    Retorna probabilidades de vitória, empate e derrota para fase de grupos.
    O empate é mais provável quando as forças são próximas.
    """
    diff = abs(team_strength - opponent_strength)
    draw_prob = max(0.18, 0.30 - diff * 0.006)
    non_draw = 1 - draw_prob
    win_share = win_probability(team_strength, opponent_strength)
    win_prob = non_draw * win_share
    loss_prob = non_draw * (1 - win_share)

    return {
        "win": round(float(win_prob), 4),
        "draw": round(float(draw_prob), 4),
        "loss": round(float(loss_prob), 4),
    }


def simulate_group_stage(group_df: pd.DataFrame, target_team: str = "Brazil", simulations: int = 10000, seed: int = 42) -> pd.DataFrame:
    """
    Simula a fase de grupos. Assume grupo com quatro seleções.
    Retorna probabilidade de terminar em 1º, 2º, 3º ou 4º.
    """
    rng = np.random.default_rng(seed)
    teams = group_df["team"].tolist()
    strengths = dict(zip(group_df["team"], group_df["strength_index"]))
    finish_counts = {1: 0, 2: 0, 3: 0, 4: 0}

    fixtures = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            fixtures.append((teams[i], teams[j]))

    for _ in range(simulations):
        points = {team: 0 for team in teams}
        goal_balance_proxy = {team: 0.0 for team in teams}

        for team_a, team_b in fixtures:
            probs = match_probabilities(strengths[team_a], strengths[team_b])
            outcome = rng.choice(["a_win", "draw", "b_win"], p=[probs["win"], probs["draw"], probs["loss"]])

            strength_diff = (strengths[team_a] - strengths[team_b]) / 20

            if outcome == "a_win":
                points[team_a] += 3
                goal_balance_proxy[team_a] += 1 + max(strength_diff, 0)
                goal_balance_proxy[team_b] -= 1 + max(strength_diff, 0)
            elif outcome == "b_win":
                points[team_b] += 3
                goal_balance_proxy[team_b] += 1 + max(-strength_diff, 0)
                goal_balance_proxy[team_a] -= 1 + max(-strength_diff, 0)
            else:
                points[team_a] += 1
                points[team_b] += 1

        table = pd.DataFrame({
            "team": teams,
            "points": [points[t] for t in teams],
            "goal_balance_proxy": [goal_balance_proxy[t] for t in teams],
            "strength_index": [strengths[t] for t in teams],
        }).sort_values(["points", "goal_balance_proxy", "strength_index"], ascending=False).reset_index(drop=True)

        position = int(table.index[table["team"] == target_team][0]) + 1
        finish_counts[position] += 1

    return pd.DataFrame([
        {"position": pos, "probability": count / simulations}
        for pos, count in finish_counts.items()
    ])


def simulate_campaign(team_strength: float = 92.0, simulations: int = 10000, seed: int = 42) -> pd.DataFrame:
    """
    Simula uma campanha simplificada de uma seleção no mata-mata.
    A dificuldade média dos adversários aumenta a cada fase.
    """
    rng = np.random.default_rng(seed)

    stage_opponent_strength = {
        "Round of 32": 74,
        "Round of 16": 80,
        "Quarterfinal": 85,
        "Semifinal": 89,
        "Final": 91,
    }

    reached = {
        "Group stage": simulations,
        "Round of 32": 0,
        "Round of 16": 0,
        "Quarterfinal": 0,
        "Semifinal": 0,
        "Final": 0,
        "Champion": 0,
    }

    group_advance_probability = min(0.97, max(0.72, 0.74 + (team_strength - 75) * 0.011))

    for _ in range(simulations):
        if rng.random() > group_advance_probability:
            continue

        reached["Round of 32"] += 1
        alive = True

        for stage, opponent_strength in stage_opponent_strength.items():
            if not alive:
                break

            if stage != "Round of 32":
                reached[stage] += 1

            p_win = win_probability(team_strength, opponent_strength, scale=10.0)
            if rng.random() > p_win:
                alive = False

        if alive:
            reached["Champion"] += 1

    return pd.DataFrame([
        {"stage": stage, "probability": count / simulations}
        for stage, count in reached.items()
    ])


def simulate_brazil_campaign(brazil_strength: float = 92.0, simulations: int = 10000, seed: int = 42) -> pd.DataFrame:
    return simulate_campaign(team_strength=brazil_strength, simulations=simulations, seed=seed)


def compare_title_contenders(strength_df: pd.DataFrame, simulations: int = 10000, seed: int = 42, top_n: int = 10) -> pd.DataFrame:
    """
    Compara as seleções mais fortes da base e estima chance relativa de título.
    A probabilidade é normalizada entre os principais contenders para facilitar leitura de dashboard.
    """
    contenders = strength_df.sort_values("strength_index", ascending=False).head(top_n).copy()
    rows = []

    for i, row in contenders.reset_index(drop=True).iterrows():
        campaign = simulate_campaign(float(row["strength_index"]), simulations=simulations, seed=seed + i)
        stage_map = dict(zip(campaign["stage"], campaign["probability"]))
        raw_title_signal = stage_map.get("Champion", 0)
        rows.append({
            "team": row["team"],
            "strength_index": float(row["strength_index"]),
            "semifinal_probability": stage_map.get("Semifinal", 0),
            "final_probability": stage_map.get("Final", 0),
            "raw_title_signal": raw_title_signal,
        })

    out = pd.DataFrame(rows)
    total_signal = out["raw_title_signal"].sum()
    if total_signal > 0:
        out["title_probability"] = out["raw_title_signal"] / total_signal
    else:
        out["title_probability"] = 0

    out["title_probability_pct"] = (out["title_probability"] * 100).round(1)
    out["final_probability_pct"] = (out["final_probability"] * 100).round(1)
    out["semifinal_probability_pct"] = (out["semifinal_probability"] * 100).round(1)

    return out.sort_values("title_probability", ascending=False).reset_index(drop=True)
