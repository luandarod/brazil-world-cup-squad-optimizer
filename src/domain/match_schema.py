from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFiniteFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class TeamMatchTruthRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    match_date: str
    stage: str
    team: str
    opponent: str
    is_home_team: bool
    goals_for: NonNegativeInt
    cards_for: NonNegativeInt
    shots_for: NonNegativeInt
    source: str

    @field_validator("match_date", mode="before")
    @classmethod
    def validate_match_date(cls, value: Any) -> str:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return date.fromisoformat(value).isoformat()
        raise TypeError("match_date must be a valid ISO date string or date-like input")


class PredictionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    team: str
    model_name: str
    target_name: str
    predicted_value: NonNegativeFiniteFloat
