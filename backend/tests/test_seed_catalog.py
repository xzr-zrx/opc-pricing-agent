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
    assert keywords["PHOTO_BLOCK_FIGURE"] == "custom photo building block figure"
    assert keywords["GRADUATION_BEAR"] == "personalized graduation teddy bear"
    assert keywords["GRADUATION_TSHIRT"] == "custom graduation t shirt"
