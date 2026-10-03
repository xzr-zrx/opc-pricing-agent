from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

Action = Literal[
    "KEEP_PRICE", "ADJUST_PRICE", "LIMITED_PROMOTION", "BUNDLE_PROMOTION",
    "NEED_MORE_DATA", "PAUSE_AND_OBSERVE"
]


class RecommendationPayload(BaseModel):
    action: Action
    suggested_price: float | None = None
    promotion: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    data_completeness: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    next_check_after_hours: int = Field(default=24, ge=1, le=168)
    need_user_inputs: list[str] = Field(default_factory=list)
