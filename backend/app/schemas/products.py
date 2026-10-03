from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str
    sku: str | None = None
    cost: float = Field(gt=0)
    current_price: float = Field(gt=0)
    min_margin_rate: float = Field(default=0.3, ge=0, lt=1)
    user_min_price: float | None = Field(default=None, gt=0)
    stock: int = Field(default=0, ge=0)
    sales_end_at: datetime | None = None
    active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    cost: float | None = Field(default=None, gt=0)
    current_price: float | None = Field(default=None, gt=0)
    min_margin_rate: float | None = Field(default=None, ge=0, lt=1)
    user_min_price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    sales_end_at: datetime | None = None
    active: bool | None = None


class ProductOut(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
