from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TeamMatchTruthRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    team: str
    opponent: str
    match_date: date
    goals_for: int = Field(ge=0)
    goals_against: int = Field(ge=0)


class PredictionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    team: str
    opponent: str
    match_date: date
    predicted_goals_for: float = Field(ge=0)
    predicted_goals_against: float = Field(ge=0)
    win_probability: float = Field(ge=0, le=1)
