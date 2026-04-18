from datetime import datetime

from pydantic import BaseModel, Field


# --- Requests ---

class CreateCharacterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role_type: str | None = None
    age: int | None = None
    gender: str | None = None
    nationality: str | None = None
    skin_tone: str | None = None
    ethnic_features: str | None = None
    appearance: str | None = None
    personality: str | None = None
    clothing: str | None = None
    symbol_meaning: str | None = None


class UpdateCharacterRequest(BaseModel):
    name: str | None = None
    role_type: str | None = None
    age: int | None = None
    gender: str | None = None
    nationality: str | None = None
    skin_tone: str | None = None
    ethnic_features: str | None = None
    appearance: str | None = None
    personality: str | None = None
    clothing: str | None = None
    symbol_meaning: str | None = None
    reference_prompt_cn: str | None = None
    reference_prompt_en: str | None = None


class GenerateReferenceRequest(BaseModel):
    provider: str | None = None


# --- Responses ---

class CharacterPeriodResponse(BaseModel):
    id: int
    period_name: str
    age: int | None
    appearance_delta: str | None
    clothing_delta: str | None
    expression: str | None
    tone: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class CharacterResponse(BaseModel):
    id: int
    name: str
    role_type: str | None
    age: int | None
    gender: str | None
    nationality: str | None
    skin_tone: str | None
    ethnic_features: str | None
    appearance: str | None
    personality: str | None
    clothing: str | None
    symbol_meaning: str | None
    reference_image_path: str | None
    reference_prompt_cn: str | None
    reference_prompt_en: str | None
    periods: list[CharacterPeriodResponse] = []
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}
