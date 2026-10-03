from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.collectors.taobao import TaobaoCollectorError, search_taobao
from app.core.config import get_settings
from app.models import Competitor, CompetitorPriceSnapshot, Product

settings = get_settings()


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


def get_latest_taobao_competitors(db: Session, product_id: int) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")

    competitors = db.scalars(
        select(Competitor).where(
            Competitor.product_id == product_id,
            Competitor.source_type == "taobao",
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
                "sales": snapshot.sales,
                "sales_text": snapshot.sales_text or str(snapshot.sales),
                "shop_name": competitor.shop_name,
                "url": competitor.url,
                "image_url": competitor.image_url,
                "source": "taobao",
                "collected_at": snapshot.collected_at.isoformat(),
            }
        )

    rows.sort(key=lambda row: row["sales"], reverse=True)
    rows = rows[:5]
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    queried_at = max((row["collected_at"] for row in rows), default=None)
    notice = f"本次仅获取到 {len(rows)} 个带销量数据的商品。" if 0 < len(rows) < 5 else None
    return {
        "product_id": product.id,
        "keyword": product.search_keyword or product.name,
        "source": "taobao",
        "queried_at": queried_at,
        "count": len(rows),
        "notice": notice,
        "items": rows,
    }


async def search_and_store_taobao(db: Session, product_id: int) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    keyword = (product.search_keyword or product.name).strip()
    if not keyword:
        raise TaobaoCollectorError("TAOBAO_KEYWORD_MISSING", "当前商品未配置淘宝搜索关键词。", 422)

    result = await search_taobao(
        keyword=keyword,
        storage_state_path=settings.taobao_storage_state_path,
        storage_state_b64=settings.taobao_storage_state_b64,
        timeout_seconds=settings.taobao_search_timeout_seconds,
        max_scan_items=settings.taobao_max_scan_items,
        headless=settings.taobao_headless,
    )
    collected_at = datetime.utcnow()

    try:
        old_active = db.scalars(
            select(Competitor).where(
                Competitor.product_id == product_id,
                Competitor.source_type == "taobao",
                Competitor.active.is_(True),
            )
        ).all()
        for competitor in old_active:
            competitor.active = False

        for item in result.items:
            competitor = db.scalar(
                select(Competitor).where(
                    Competitor.product_id == product_id,
                    Competitor.source_type == "taobao",
                    Competitor.url == item.url,
                ).limit(1)
            )
            if competitor is None:
                competitor = Competitor(
                    product_id=product_id,
                    name=item.title,
                    source_type="taobao",
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
                    "price": item.price,
                    "sales": item.sales,
                    "sales_text": item.sales_text,
                    "shop_name": item.shop_name,
                    "url": item.url,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            db.add(
                CompetitorPriceSnapshot(
                    competitor_id=competitor.id,
                    price=item.price,
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
        raise TaobaoCollectorError("TAOBAO_DB_WRITE_FAILED", "淘宝竞品已获取，但写入数据库失败。", 500) from exc

    payload = get_latest_taobao_competitors(db, product_id)
    payload["scanned_count"] = result.scanned_count
    payload["valid_count"] = result.valid_count
    if len(result.items) < 5:
        payload["notice"] = f"本次仅获取到 {len(result.items)} 个带销量数据的商品。"
    else:
        payload["notice"] = "Top5 为本次淘宝搜索结果中按页面显示销量排序后的前 5 个有效商品。"
    return payload
