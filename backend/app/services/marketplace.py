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
SOURCE_TYPE = "pdd_ddk"
LEGACY_EXTERNAL_SOURCES = {"taobao", "google_shopping", SOURCE_TYPE}


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
        if not snapshot or snapshot.price is None or snapshot.sales is None:
            continue
        rows.append(
            {
                "competitor_id": competitor.id,
                "title": competitor.name,
                "price": snapshot.price,
                "sales": int(snapshot.sales),
                "sales_text": snapshot.sales_text or str(snapshot.sales),
                "shop_name": competitor.shop_name,
                "url": competitor.url,
                "image_url": competitor.image_url,
                "source": SOURCE_TYPE,
                "collected_at": snapshot.collected_at.isoformat(),
            }
        )

    rows.sort(key=lambda row: row["sales"], reverse=True)
    rows = rows[:5]
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    queried_at = max((row["collected_at"] for row in rows), default=None)
    notice = f"本次仅获取到 {len(rows)} 个带有效销量数据的商品。" if 0 < len(rows) < 5 else None
    return {
        "product_id": product.id,
        "keyword": product.search_keyword or product.name,
        "source": SOURCE_TYPE,
        "provider_name": "拼多多 / 多多进宝",
        "queried_at": queried_at,
        "count": len(rows),
        "ranking_metric": "sales_tip",
        "ranking_label": "销量",
        "currency": "CNY",
        "price_note": "价格来自多多进宝商品搜索接口，单位统一为人民币元。",
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
        client_id=settings.pdd_client_id,
        client_secret=settings.pdd_client_secret,
        pid=settings.pdd_pid,
        custom_parameters=settings.pdd_custom_parameters,
        timeout_seconds=settings.pdd_timeout_seconds,
        max_scan_items=settings.pdd_max_scan_items,
    )
    collected_at = datetime.utcnow()

    try:
        # 一次查询成功后，只让当前 PDD Top5 作为“当前外部竞品”。
        # 老淘宝/Google Shopping 历史快照仍保留，但不继续显示为 active。
        old_external = db.scalars(
            select(Competitor).where(
                Competitor.product_id == product_id,
                Competitor.source_type.in_(LEGACY_EXTERNAL_SOURCES),
                Competitor.active.is_(True),
            )
        ).all()
        for competitor in old_external:
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

            raw = json.dumps(
                {
                    "title": item.title,
                    "price_cny": item.price_cny,
                    "sales": item.sales,
                    "sales_text": item.sales_text,
                    "shop_name": item.shop_name,
                    "url": item.url,
                    "goods_id": item.goods_id,
                    "goods_sign": item.goods_sign,
                    "original_price_cents": item.original_price_cents,
                    "request_id": result.request_id,
                    "search_id": result.search_id,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            db.add(
                CompetitorPriceSnapshot(
                    competitor_id=competitor.id,
                    price=item.price_cny,
                    promo_text=None,
                    sales=item.sales,
                    sales_text=item.sales_text,
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
    payload["request_id"] = result.request_id
    if len(result.items) < 5:
        payload["notice"] = f"本次仅获取到 {len(result.items)} 个带有效销量数据的商品。"
    else:
        payload["notice"] = "Top5 为本次拼多多搜索结果中成功获取到销量数据的商品，按接口展示销量排序；不代表拼多多全平台绝对销量前5。"
    return payload
