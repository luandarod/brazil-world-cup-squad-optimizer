import numpy as np
import pandas as pd


TEAM_COMPONENT_WEIGHTS = {
    "base_strength": 0.25,
    "attack_score": 0.17,
    "midfield_score": 0.13,
    "defense_score": 0.13,
    "goalkeeper_score": 0.08,
    "recent_form_score": 0.10,
    "tournament_history_score": 0.07,
    "market_depth_score": 0.07,
}


def win_probability(team_strength: float, opponent_strength: float, scale: float = 12.0) -> float:
    """
    Simplified win probability from the difference between two team strength indexes.
    """
    diff = team_strength - opponent_strength
    return 1 / (1 + np.exp(-diff / scale))


def match_probabilities(team_strength: float, opponent_strength: float) -> dict:
    """
    Group-stage probabilities: win, draw and loss.
    Draw probability is higher when teams have similar strength.
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


def calculate_composite_strength(components_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds a composite team-strength index from interpretable components.
    This replaces a single opaque manual strength number.
    """
    df = components_df.copy()
    df["composite_strength"] = 0.0

    for feature, weight in TEAM_COMPONENT_WEIGHTS.items():
        if feature not in df.columns:
            raise ValueError(f"Missing component column: {feature}")
        df["composite_strength"] += df[feature].astype(float) * weight

    if "confidence_score" in df.columns:
        # Low-confidence teams are slightly pulled toward the field average.
        mean_strength = df["composite_strength"].mean()
        confidence = df["confidence_score"].clip(0, 1)
        df["adjusted_strength"] = df["composite_strength"] * confidence + mean_strength * (1 - confidence)
    else:
        df["adjusted_strength"] = df["composite_strength"]

    df["adjusted_strength"] = df["adjusted_strength"].round(2)
    return df


def simulate_group_stage(group_df: pd.DataFrame, target_team: str = "Brazil", simulations: int = 10000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    teams = group_df["team"].tolist()
    strength_col = "adjusted_strength" if "adjusted_strength" in group_df.columns else "strength_index"
    strengths = dict(zip(group_df["team"], group_df[strength_col]))
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
            "strength": [strengths[t] for t in teams],
        }).sort_values(["points", "goal_balance_proxy", "strength"], ascending=False).reset_index(drop=True)

        position = int(table.index[table["team"] == target_team][0]) + 1
        finish_counts[position] += 1

    return pd.DataFrame([
        {"position": pos, "probability": count / simulations}
        for pos, count in finish_counts.items()
    ])


def simulate_campaign(team_strength: float = 92.0, simulations: int = 10000, seed: int = 42) -> pd.DataFrame:
    """
    Simplified campaign simulation. Knockout difficulty increases by phase.
    This is still a portfolio forecasting layer, not a betting model.
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
    Backwards-compatible title comparison using a single strength_index column.
    """
    contenders = strength_df.sort_values("strength_index", ascending=False).head(top_n).copy()
    return _compare_strength_values(contenders, "strength_index", simulations, seed)


def compare_title_contenders_components(components_df: pd.DataFrame, simulations: int = 10000, seed: int = 42, top_n: int = 10) -> pd.DataFrame:
    """
    More robust title comparison using a composite strength index.
    Components include attack, midfield, defense, goalkeeper, form, history and squad depth.
    """
    scored = calculate_composite_strength(components_df)
    contenders = scored.sort_values("adjusted_strength", ascending=False).head(top_n).copy()
    out = _compare_strength_values(contenders, "adjusted_strength", simulations, seed)

    component_cols = [
        "base_strength",
        "attack_score",
        "midfield_score",
        "defense_score",
        "goalkeeper_score",
        "recent_form_score",
        "tournament_history_score",
        "market_depth_score",
        "confidence_score",
        "composite_strength",
        "adjusted_strength",
    ]
    return out.merge(contenders[["team"] + component_cols], on="team", how="left")


def _compare_strength_values(contenders: pd.DataFrame, strength_col: str, simulations: int, seed: int) -> pd.DataFrame:
    rows = []

    for i, row in contenders.reset_index(drop=True).iterrows():
        campaign = simulate_campaign(float(row[strength_col]), simulations=simulations, seed=seed + i)
        stage_map = dict(zip(campaign["stage"], campaign["probability"]))
        raw_title_signal = stage_map.get("Champion", 0)
        rows.append({
            "team": row["team"],
            "model_strength": float(row[strength_col]),
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
