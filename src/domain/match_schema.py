from pydantic import BaseModel, ConfigDict


class TeamMatchTruthRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    match_date: str
    stage: str
    team: str
    opponent: str
    is_home_team: bool
    goals_for: int
    cards_for: int
    shots_for: int
    source: str


class PredictionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    team: str
    model_name: str
    target_name: str
    predicted_value: float
