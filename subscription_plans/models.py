from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Price(BaseModel):
    monthly: float = Field(..., ge=0, description="Monthly subscription price.")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code.")


class AddOn(BaseModel):
    name: str = Field(..., min_length=1)
    price_delta: float = Field(..., ge=0)
    description: Optional[str] = None


class Plan(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)
    tier: str = Field(..., min_length=1)
    price: Price
    device_limit: int = Field(..., ge=0, le=8)
    video_quality: str = Field(..., min_length=2)
    add_ons: List[AddOn] = Field(default_factory=list)
    description: Optional[str] = None

    @validator("tier")
    def normalize_tier(cls, value: str) -> str:
        return value.title()


class PlanDocument(BaseModel):
    version: str = Field("1.0", description="Document schema version.")
    plans: List[Plan]
    metadata: Optional[dict] = None


@dataclass
class PlanGenerationConfig:
    """Configuration for the plan generation pipeline."""

    max_retries: int = 3
    examples_to_include: int = 3
    schema_path: Optional[str] = None
    enable_ab_testing: bool = True


@dataclass
class PlanGenerationResult:
    prompt: str
    yaml_output: str
    document: PlanDocument
    validation_warnings: List[str]


@dataclass
class PlanVariant:
    label: str
    result: PlanGenerationResult
    justification: str

