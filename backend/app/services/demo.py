from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Competitor, CompetitorPriceSnapshot, Product, SalesDaily
from app.services.monitor import collect_competitor


DEMO_PRODUCTS = [
    {
        "name": "照片定制积木人像",
        "sku": "PHOTO_BLOCK_FIGURE",
        "search_keyword": "照片定制积木人像",
        "cost": 25.0,
        "current_price": 69.0,
        "stock": 80,
    },
    {
        "name": "定制毕业小熊",
        "sku": "GRADUATION_BEAR",
        "search_keyword": "毕业小熊 定制",
        "cost": 22.0,
        "current_price": 59.0,
        "stock": 100,
    },
    {
        "name": "毕业纪念T恤",
        "sku": "GRADUATION_TSHIRT",
        "search_keyword": "毕业纪念T恤 定制",
        "cost": 20.0,
        "current_price": 59.0,
        "stock": 120,
    },
]


def _ensure_mock_data(db: Session, product: Product) -> list[Competitor]:
    comps = db.scalars(
        select(Competitor).where(
            Competitor.product_id == product.id,
            Competitor.source_type == "mock",
        )
    ).all()
    if not comps:
        base = float(product.current_price)
        configs = [
            ("竞品 A", [base, round(base * 0.83, 2), round(base * 0.83, 2)], ["", "限时直降", "限时直降"]),
            ("竞品 B", [round(base * 0.93, 2)] * 3, ["", "", "第二件优惠"]),
            ("竞品 C", [round(base * 1.05, 2), round(base * 1.05, 2), round(base * 0.98, 2)], ["", "", "小幅降价"]),
        ]
        for name, prices, promos in configs:
            c = Competitor(
                product_id=product.id,
                name=name,
                source_type="mock",
                mock_prices_json=json.dumps(prices),
                mock_promos_json=json.dumps(promos, ensure_ascii=False),
                mock_index=0,
                active=True,
            )
            db.add(c)
            comps.append(c)
        db.flush()

    sales_count = db.scalar(select(func.count(SalesDaily.id)).where(SalesDaily.product_id == product.id)) or 0
    if sales_count == 0:
        for i, qty in enumerate([10, 9, 8, 8, 7, 6, 5]):
            d = date.today() - timedelta(days=6 - i)
            db.add(
                SalesDaily(
                    product_id=product.id,
                    sale_date=d,
                    quantity=qty,
                    revenue=qty * product.current_price,
                )
            )
    return comps


def seed_demo_catalog(db: Session) -> list[Product]:
    """幂等创建比赛演示所需的三个商品，并补齐 Demo mock/销量基础数据。"""
    products: list[Product] = []

    # 兼容旧版本唯一的 DEMO-TSHIRT，直接迁移 SKU，保留其历史记录和 Agent Run。
    legacy_tshirt = db.scalar(select(Product).where(Product.sku == "DEMO-TSHIRT"))
    new_tshirt = db.scalar(select(Product).where(Product.sku == "GRADUATION_TSHIRT"))
    if legacy_tshirt and not new_tshirt:
        legacy_tshirt.sku = "GRADUATION_TSHIRT"
        new_tshirt = legacy_tshirt

    for config in DEMO_PRODUCTS:
        product = db.scalar(select(Product).where(Product.sku == config["sku"]))
        if product is None:
            product = Product(
                name=config["name"],
                sku=config["sku"],
                search_keyword=config["search_keyword"],
                cost=config["cost"],
                current_price=config["current_price"],
                min_margin_rate=0.30,
                stock=config["stock"],
                active=True,
            )
            db.add(product)
            db.flush()
        else:
            # 名称、SKU、电商搜索关键词和用户明确给出的成本属于系统基础配置；
            # 已存在商品的当前售价/库存不覆盖，避免启动时重置用户后续演示操作。
            product.name = config["name"]
            product.search_keyword = config["search_keyword"]
            product.cost = config["cost"]
            product.active = True

        _ensure_mock_data(db, product)
        products.append(product)

    db.commit()
    for product in products:
        db.refresh(product)
        comps = db.scalars(
            select(Competitor).where(
                Competitor.product_id == product.id,
                Competitor.source_type == "mock",
            )
        ).all()
        for comp in comps:
            snapshot_count = db.scalar(
                select(func.count(CompetitorPriceSnapshot.id)).where(
                    CompetitorPriceSnapshot.competitor_id == comp.id
                )
            ) or 0
            if snapshot_count == 0:
                collect_competitor(db, comp.id, advance=False)
    return products


def seed_demo(db: Session) -> Product:
    """保留原有 /demo/seed 和测试调用习惯，返回毕业纪念 T 恤。"""
    products = seed_demo_catalog(db)
    return next(p for p in products if p.sku == "GRADUATION_TSHIRT")


def advance_demo(db: Session, product_id: int) -> list[dict]:
    comps = db.scalars(
        select(Competitor).where(
            Competitor.product_id == product_id,
            Competitor.source_type == "mock",
        )
    ).all()
    out = []
    for c in comps:
        snap, event = collect_competitor(db, c.id, advance=True)
        out.append(
            {
                "competitor_id": c.id,
                "price": snap.price,
                "promo_text": snap.promo_text,
                "event_id": event.id if event else None,
            }
        )
    return out
