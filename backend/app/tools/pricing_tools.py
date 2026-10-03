from __future__ import annotations

from datetime import date, timedelta
from statistics import mean
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.models import Competitor, CompetitorPriceSnapshot, Product, SalesDaily


class ProductIdArgs(BaseModel):
    product_id: int = Field(gt=0)


class SalesSummaryArgs(ProductIdArgs):
    days: int = Field(default=7, ge=1, le=90)


class MarginArgs(ProductIdArgs):
    candidate_price: float = Field(gt=0)


class SimulateArgs(ProductIdArgs):
    candidate_list: list[float] = Field(min_length=1, max_length=10)
    strategy: str = "compare"


def min_safe_price(product: Product) -> float:
    margin_floor = product.cost / (1 - product.min_margin_rate)
    return round(max(margin_floor, product.user_min_price or 0), 2)


def get_competitor_context(db: Session, product_id: int) -> dict:
    competitors = db.scalars(select(Competitor).where(Competitor.product_id == product_id, Competitor.active.is_(True))).all()
    result = []
    for c in competitors:
        snaps = db.scalars(
            select(CompetitorPriceSnapshot)
            .where(CompetitorPriceSnapshot.competitor_id == c.id, CompetitorPriceSnapshot.success.is_(True))
            .order_by(desc(CompetitorPriceSnapshot.collected_at)).limit(5)
        ).all()
        latest = snaps[0] if snaps else None
        previous = snaps[1] if len(snaps) > 1 else None
        change_percent = None
        if latest and previous and previous.price:
            change_percent = round((latest.price - previous.price) / previous.price * 100, 2)
        result.append({
            "competitor_id": c.id, "name": c.name,
            "current_price": latest.price if latest else None,
            "promo_text": latest.promo_text if latest else None,
            "change_percent": change_percent,
            "recent_prices": [s.price for s in reversed(snaps) if s.price is not None],
        })
    return {"product_id": product_id, "competitors": result}


def get_sales_summary(db: Session, product_id: int, days: int = 7) -> dict:
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = db.scalars(select(SalesDaily).where(
        SalesDaily.product_id == product_id,
        SalesDaily.sale_date >= start,
        SalesDaily.sale_date <= end,
    ).order_by(SalesDaily.sale_date)).all()
    quantities = [r.quantity for r in rows]
    total = sum(quantities)
    avg = round(total / days, 2)
    half = max(1, len(quantities) // 2)
    first = mean(quantities[:half]) if quantities else 0
    second = mean(quantities[-half:]) if quantities else 0
    trend_pct = round((second - first) / first * 100, 2) if first else (100.0 if second > 0 else 0.0)
    return {
        "product_id": product_id, "days": days, "data_days": len(rows),
        "total_quantity": total, "daily_average": avg, "trend_percent": trend_pct,
        "trend": "up" if trend_pct > 5 else "down" if trend_pct < -5 else "stable",
    }


def get_inventory_status(db: Session, product_id: int) -> dict:
    p = db.get(Product, product_id)
    if not p:
        raise ValueError("product not found")
    sales = get_sales_summary(db, product_id, 7)
    avg = sales["daily_average"]
    days_cover = round(p.stock / avg, 1) if avg > 0 else None
    return {"product_id": product_id, "stock": p.stock, "estimated_days_cover": days_cover}


def calculate_margin(db: Session, product_id: int, candidate_price: float) -> dict:
    p = db.get(Product, product_id)
    if not p:
        raise ValueError("product not found")
    profit = candidate_price - p.cost
    margin_rate = profit / candidate_price
    floor = min_safe_price(p)
    return {
        "product_id": product_id,
        "candidate_price": round(candidate_price, 2),
        "unit_profit": round(profit, 2),
        "margin_rate": round(margin_rate, 4),
        "min_safe_price": floor,
        "below_floor": candidate_price + 1e-9 < floor,
    }


def simulate_pricing_options(db: Session, product_id: int, candidate_list: list[float], strategy: str = "compare") -> dict:
    p = db.get(Product, product_id)
    if not p:
        raise ValueError("product not found")
    options = []
    for price in candidate_list:
        m = calculate_margin(db, product_id, price)
        m["change_percent"] = round((price - p.current_price) / p.current_price * 100, 2)
        m["discount_cost_per_unit"] = round(max(0, p.current_price - price), 2)
        options.append(m)
    return {"product_id": product_id, "strategy": strategy, "options": options}


TOOL_SCHEMAS = [
    {"type":"function","function":{"name":"get_competitor_context","description":"读取竞品当前与近期价格、促销和变化幅度","parameters":ProductIdArgs.model_json_schema()}},
    {"type":"function","function":{"name":"get_sales_summary","description":"读取并计算最近销量汇总和趋势","parameters":SalesSummaryArgs.model_json_schema()}},
    {"type":"function","function":{"name":"get_inventory_status","description":"读取当前库存及可售天数","parameters":ProductIdArgs.model_json_schema()}},
    {"type":"function","function":{"name":"calculate_margin","description":"确定性计算候选价格的毛利、毛利率和最低安全售价","parameters":MarginArgs.model_json_schema()}},
    {"type":"function","function":{"name":"simulate_pricing_options","description":"比较多个候选价格的毛利和价格变化幅度","parameters":SimulateArgs.model_json_schema()}},
]


def execute_tool(db: Session, name: str, arguments: dict) -> dict:
    if name == "get_competitor_context":
        args = ProductIdArgs.model_validate(arguments)
        return get_competitor_context(db, args.product_id)
    if name == "get_sales_summary":
        args = SalesSummaryArgs.model_validate(arguments)
        return get_sales_summary(db, args.product_id, args.days)
    if name == "get_inventory_status":
        args = ProductIdArgs.model_validate(arguments)
        return get_inventory_status(db, args.product_id)
    if name == "calculate_margin":
        args = MarginArgs.model_validate(arguments)
        return calculate_margin(db, args.product_id, args.candidate_price)
    if name == "simulate_pricing_options":
        args = SimulateArgs.model_validate(arguments)
        return simulate_pricing_options(db, args.product_id, args.candidate_list, args.strategy)
    raise ValueError(f"unknown tool: {name}")
