from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from statistics import mean

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Competitor, CompetitorPriceSnapshot, Product, ProductPriceSnapshot

MAX_RANGE_DAYS = 7


def normalize_date_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=MAX_RANGE_DAYS - 1))
    if end < start:
        raise ValueError("结束日期不能早于开始日期")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise ValueError("单次最多查看7天价格趋势")
    return start, end


def ensure_product_price_snapshot(
    db: Session,
    product: Product,
    *,
    source_type: str = "system",
    recorded_at: datetime | None = None,
) -> ProductPriceSnapshot:
    """为商品保存可验证的自身价格快照；同一天同来源只保留一次最新状态。"""
    now = recorded_at or datetime.utcnow()
    start_dt = datetime.combine(now.date(), time.min)
    end_dt = datetime.combine(now.date(), time.max)
    row = db.scalar(
        select(ProductPriceSnapshot)
        .where(
            ProductPriceSnapshot.product_id == product.id,
            ProductPriceSnapshot.source_type == source_type,
            ProductPriceSnapshot.recorded_at >= start_dt,
            ProductPriceSnapshot.recorded_at <= end_dt,
        )
        .order_by(desc(ProductPriceSnapshot.recorded_at), desc(ProductPriceSnapshot.id))
        .limit(1)
    )
    if row:
        row.price = float(product.current_price)
        row.recorded_at = now
        return row
    row = ProductPriceSnapshot(
        product_id=product.id,
        price=float(product.current_price),
        source_type=source_type,
        recorded_at=now,
    )
    db.add(row)
    return row


def _date_sequence(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _latest_snapshots_per_competitor_day(
    rows: list[tuple[CompetitorPriceSnapshot, int]],
) -> dict[date, list[CompetitorPriceSnapshot]]:
    latest: dict[tuple[date, int], CompetitorPriceSnapshot] = {}
    for snap, competitor_id in rows:
        key = (snap.collected_at.date(), competitor_id)
        previous = latest.get(key)
        if previous is None or snap.collected_at >= previous.collected_at:
            latest[key] = snap
    by_day: dict[date, list[CompetitorPriceSnapshot]] = defaultdict(list)
    for (day, _), snap in latest.items():
        by_day[day].append(snap)
    return by_day


def get_price_trend(
    db: Session,
    product_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    *,
    mode: str = "real",
) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    start, end = normalize_date_range(start_date, end_date)
    if mode not in {"real", "demo"}:
        raise ValueError("mode 仅支持 real 或 demo")

    range_start = datetime.combine(start, time.min)
    range_end = datetime.combine(end, time.max)
    competitor_source = "pdd_ddk" if mode == "real" else "mock"
    own_source = "system" if mode == "real" else "demo"

    competitor_rows = db.execute(
        select(CompetitorPriceSnapshot, Competitor.id)
        .join(Competitor, Competitor.id == CompetitorPriceSnapshot.competitor_id)
        .where(
            Competitor.product_id == product_id,
            Competitor.source_type == competitor_source,
            CompetitorPriceSnapshot.success.is_(True),
            CompetitorPriceSnapshot.price.is_not(None),
            CompetitorPriceSnapshot.collected_at >= range_start,
            CompetitorPriceSnapshot.collected_at <= range_end,
        )
        .order_by(CompetitorPriceSnapshot.collected_at)
    ).all()
    competitor_by_day = _latest_snapshots_per_competitor_day(competitor_rows)

    own_rows = db.scalars(
        select(ProductPriceSnapshot)
        .where(
            ProductPriceSnapshot.product_id == product_id,
            ProductPriceSnapshot.source_type == own_source,
            ProductPriceSnapshot.recorded_at >= range_start,
            ProductPriceSnapshot.recorded_at <= range_end,
        )
        .order_by(ProductPriceSnapshot.recorded_at)
    ).all()
    own_latest_by_day: dict[date, ProductPriceSnapshot] = {}
    for row in own_rows:
        own_latest_by_day[row.recorded_at.date()] = row

    # 对真实价格只允许从“已记录的已知价格”向后延续，不向首次记录之前反向补造历史。
    previous_own = db.scalar(
        select(ProductPriceSnapshot)
        .where(
            ProductPriceSnapshot.product_id == product_id,
            ProductPriceSnapshot.source_type == own_source,
            ProductPriceSnapshot.recorded_at < range_start,
        )
        .order_by(desc(ProductPriceSnapshot.recorded_at), desc(ProductPriceSnapshot.id))
        .limit(1)
    )
    carried_price = float(previous_own.price) if previous_own else None

    daily = []
    market_avg_values: list[float] = []
    market_data_days = 0
    raw_own_days = len(own_latest_by_day)
    total_samples = 0
    for day in _date_sequence(start, end):
        own_observed = own_latest_by_day.get(day)
        if own_observed:
            carried_price = float(own_observed.price)
        market_rows = competitor_by_day.get(day, [])
        prices = [float(row.price) for row in market_rows if row.price is not None]
        sales_values = [int(row.sales or 0) for row in market_rows if row.sales is not None]
        avg_price = round(mean(prices), 2) if prices else None
        if avg_price is not None:
            market_avg_values.append(avg_price)
            market_data_days += 1
        total_samples += len(prices)
        daily.append(
            {
                "date": day.isoformat(),
                "own_price": round(carried_price, 2) if carried_price is not None else None,
                "own_price_observed": own_observed is not None,
                "competitor_avg_price": avg_price,
                "competitor_min_price": round(min(prices), 2) if prices else None,
                "competitor_max_price": round(max(prices), 2) if prices else None,
                "competitor_count": len(prices),
                "competitor_sales_total": sum(sales_values) if sales_values else None,
            }
        )

    first_avg = market_avg_values[0] if market_avg_values else None
    latest_avg = market_avg_values[-1] if market_avg_values else None
    trend_percent = None
    trend = "insufficient"
    if first_avg is not None and latest_avg is not None and market_data_days >= 2:
        trend_percent = round((latest_avg - first_avg) / first_avg * 100, 2) if first_avg else 0.0
        trend = "up" if trend_percent > 3 else "down" if trend_percent < -3 else "stable"

    flat_prices = [
        float(row.price)
        for rows in competitor_by_day.values()
        for row in rows
        if row.price is not None
    ]
    history_insufficient = market_data_days < 2
    if mode == "demo":
        notice = "当前展示的是明确标记的 Demo 历史数据，仅用于演示7天趋势，不代表拼多多真实历史。"
    elif history_insufficient:
        notice = "真实竞品历史数据不足，从首次成功采集日期开始展示；系统不会随机补造缺失的拼多多历史价格。"
    else:
        notice = "趋势仅基于所选7天范围内实际入库的拼多多竞品快照。"

    return {
        "product_id": product_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days": (end - start).days + 1,
        "mode": mode,
        "source": competitor_source,
        "source_label": "拼多多 · 多多进宝真实历史" if mode == "real" else "Demo 历史数据",
        "history_insufficient": history_insufficient,
        "notice": notice,
        "summary": {
            "current_price": float(product.current_price),
            "period_market_avg_price": round(mean(flat_prices), 2) if flat_prices else None,
            "period_market_min_price": round(min(flat_prices), 2) if flat_prices else None,
            "period_market_max_price": round(max(flat_prices), 2) if flat_prices else None,
            "first_market_avg_price": first_avg,
            "latest_market_avg_price": latest_avg,
            "trend_percent": trend_percent,
            "trend": trend,
            "market_data_days": market_data_days,
            "own_observed_days": raw_own_days,
            "competitor_samples": total_samples,
        },
        "daily": daily,
    }
