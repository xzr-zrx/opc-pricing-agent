from sqlalchemy import select

from app.models import Product
from app.services.demo import seed_demo_catalog


def test_three_products_are_seeded_idempotently(db):
    seed_demo_catalog(db)
    seed_demo_catalog(db)
    rows = db.scalars(select(Product).where(Product.sku.in_([
        "PHOTO_BLOCK_FIGURE", "GRADUATION_BEAR", "GRADUATION_TSHIRT"
    ])).order_by(Product.sku)).all()
    assert len(rows) == 3
    costs = {row.sku: row.cost for row in rows}
    assert costs == {
        "PHOTO_BLOCK_FIGURE": 25.0,
        "GRADUATION_BEAR": 22.0,
        "GRADUATION_TSHIRT": 20.0,
    }
    keywords = {row.sku: row.search_keyword for row in rows}
    assert keywords["PHOTO_BLOCK_FIGURE"] == "照片定制积木人像"
    assert keywords["GRADUATION_BEAR"] == "毕业小熊 定制"
    assert keywords["GRADUATION_TSHIRT"] == "毕业纪念T恤 定制"
