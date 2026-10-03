from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.collectors.marketplace import MarketplaceCollectorError, search_marketplace
from app.core.config import get_settings
from app.models import Competitor, CompetitorPriceSnapshot, Product

settings = get_settings()
SOURCE_TYPE = "google_shopping"


def _latest_snapshot(db: Session, competitor_id: int) -> CompetitorPriceSnapshot | None:
    return db.scalar(
        select(CompetitorPriceSnapshot)
        .where(
            CompetitorPriceSnapshot.competitor_id == competitor_id,
            CompetitorPriceSnapshot.success.is_(True),
        )
        .order_by(desc(CompetitorPriceSnapshot.collected_at), desc(CompetitorPriceSnapshot.id))
        .limit(1)
    )


def get_latest_marketplace_competitors(db: Session, product_id: int) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")

    competitors = db.scalars(
        select(Competitor).where(
            Competitor.product_id == product_id,
            Competitor.source_type == SOURCE_TYPE,
            Competitor.active.is_(True),
        )
    ).all()

    rows = []
    for competitor in competitors:
        snapshot = _latest_snapshot(db, competitor.id)
        if not snapshot or snapshot.price is None:
            continue
        popularity = int(snapshot.sales or 0)  # 复用旧字段存“评论数/热度”，不把它对外称作销量。
        rows.append(
            {
                "competitor_id": competitor.id,
                "title": competitor.name,
                "price": snapshot.price,
                "popularity": popularity,
                "popularity_text": snapshot.sales_text or f"{popularity}条评价",
                "rating_text": snapshot.promo_text,
                "shop_name": competitor.shop_name,
                "url": competitor.url,
                "image_url": competitor.image_url,
                "source": SOURCE_TYPE,
                "collected_at": snapshot.collected_at.isoformat(),
            }
        )

    rows.sort(key=lambda row: row["popularity"], reverse=True)
    rows = rows[:5]
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    queried_at = max((row["collected_at"] for row in rows), default=None)
    notice = f"本次仅获取到 {len(rows)} 个有效商品。" if 0 < len(rows) < 5 else None
    return {
        "product_id": product.id,
        "keyword": product.search_keyword or product.name,
        "source": SOURCE_TYPE,
        "provider_name": "Google Shopping / Serper",
        "queried_at": queried_at,
        "count": len(rows),
        "ranking_metric": "rating_count",
        "ranking_label": "评论数热度",
        "currency": "CNY",
        "price_note": "外币报价按查询时公开汇率折算为人民币，仅用于竞品参考。",
        "notice": notice,
        "items": rows,
    }


async def search_and_store_marketplace(db: Session, product_id: int) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")

    keyword = (product.search_keyword or product.name).strip()
    if not keyword:
        raise MarketplaceCollectorError("MARKETPLACE_KEYWORD_MISSING", "当前商品未配置电商搜索关键词。", 422)

    result = await search_marketplace(
        keyword=keyword,
        api_key=settings.serper_api_key,
        timeout_seconds=settings.serper_timeout_seconds,
        country=settings.serper_country,
        language=settings.serper_language,
        max_scan_items=settings.serper_max_scan_items,
    )
    collected_at = datetime.utcnow()

    try:
        old_active = db.scalars(
            select(Competitor).where(
                Competitor.product_id == product_id,
                Competitor.source_type == SOURCE_TYPE,
                Competitor.active.is_(True),
            )
        ).all()
        for competitor in old_active:
            competitor.active = False

        for item in result.items:
            competitor = db.scalar(
                select(Competitor)
                .where(
                    Competitor.product_id == product_id,
                    Competitor.source_type == SOURCE_TYPE,
                    Competitor.url == item.url,
                )
                .limit(1)
            )
            if competitor is None:
                competitor = Competitor(
                    product_id=product_id,
                    name=item.title,
                    source_type=SOURCE_TYPE,
                    url=item.url,
                    shop_name=item.shop_name,
                    image_url=item.image_url,
                    active=True,
                )
                db.add(competitor)
                db.flush()
            else:
                competitor.name = item.title
                competitor.shop_name = item.shop_name
                competitor.image_url = item.image_url
                competitor.active = True

            rating_text = f"评分 {item.rating:.1f}" if item.rating is not None else None
            raw = json.dumps(
                {
                    "title": item.title,
                    "price_cny": item.price_cny,
                    "original_price_text": item.original_price_text,
                    "popularity": item.popularity,
                    "shop_name": item.shop_name,
                    "url": item.url,
                    "rating": item.rating,
                    "usd_cny_rate": result.usd_cny_rate,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            db.add(
                CompetitorPriceSnapshot(
                    competitor_id=competitor.id,
                    price=item.price_cny,
                    promo_text=rating_text,
                    # 旧表字段名叫 sales。Google Shopping 没有销量，因此只把
                    # ratingCount 存在这里作为“市场热度数值”，对外一律标注 popularity。
                    sales=item.popularity,
                    sales_text=item.popularity_text,
                    collected_at=collected_at,
                    success=True,
                    raw_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                )
            )

        db.commit()
    except Exception as exc:
        db.rollback()
        raise MarketplaceCollectorError(
            "MARKETPLACE_DB_WRITE_FAILED",
            "电商竞品已获取，但写入数据库失败。",
            500,
        ) from exc

    payload = get_latest_marketplace_competitors(db, product_id)
    payload["scanned_count"] = result.scanned_count
    payload["valid_count"] = result.valid_count
    payload["usd_cny_rate"] = result.usd_cny_rate
    if len(result.items) < 5:
        payload["notice"] = f"本次仅获取到 {len(result.items)} 个有效商品。"
    else:
        payload["notice"] = "Top5 按 Google Shopping 搜索结果中的评论/评分数量排序，代表市场热度，不等于销量。"
    return payload
