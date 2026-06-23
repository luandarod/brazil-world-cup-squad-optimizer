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
    fouls_for: NonNegativeInt = 0
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


class PublicMatchTruthRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    match_date: str
    stage: str
    home_team: str
    away_team: str
    home_goals: NonNegativeInt | None = None
    away_goals: NonNegativeInt | None = None
    home_shots: NonNegativeInt | None = None
    away_shots: NonNegativeInt | None = None
    home_cards: NonNegativeInt | None = None
    away_cards: NonNegativeInt | None = None
    home_fouls: NonNegativeInt | None = None
    away_fouls: NonNegativeInt | None = None
    status: str
    source: str
    source_retrieved_at: str | None = None
    is_future_fixture: bool = False
    home_lineup_confirmed: bool = False
    away_lineup_confirmed: bool = False
    home_probable_lineup_count: NonNegativeInt = 0
    away_probable_lineup_count: NonNegativeInt = 0
    home_substitutions_used: NonNegativeInt = 0
    away_substitutions_used: NonNegativeInt = 0

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
