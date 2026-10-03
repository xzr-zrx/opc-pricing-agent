from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cost: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float)
    min_margin_rate: Mapped[float] = mapped_column(Float, default=0.3)
    user_min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    sales_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    competitors = relationship("Competitor", cascade="all, delete-orphan", back_populates="product")


class Competitor(Base):
    __tablename__ = "competitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(30), default="mock")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_selector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    promo_selector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    manual_promo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mock_prices_json: Mapped[str] = mapped_column(Text, default="[]")
    mock_promos_json: Mapped[str] = mapped_column(Text, default="[]")
    mock_index: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    product = relationship("Product", back_populates="competitors")
    snapshots = relationship("CompetitorPriceSnapshot", cascade="all, delete-orphan")


class CompetitorPriceSnapshot(Base):
    __tablename__ = "competitor_price_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id", ondelete="CASCADE"), index=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    promo_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SalesDaily(Base):
    __tablename__ = "sales_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sale_date: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)


class PricingEvent(Base):
    __tablename__ = "pricing_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    competitor_id: Mapped[int | None] = mapped_column(ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("pricing_events.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(60), default="demo")
    model: Mapped[str] = mapped_column(String(120), default="demo")
    status: Mapped[str] = mapped_column(String(30), default="running")
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str] = mapped_column(String(120))
    arguments_json: Mapped[str] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class PricingRecommendation(Base):
    __tablename__ = "pricing_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    suggested_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    promotion_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    risks_json: Mapped[str] = mapped_column(Text, default="[]")
    data_completeness: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    next_check_after_hours: Mapped[int] = mapped_column(Integer, default=24)
    need_user_inputs_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
