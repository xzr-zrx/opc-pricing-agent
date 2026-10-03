from datetime import date, datetime, timedelta

from app.models import Competitor, CompetitorPriceSnapshot, Product
from app.services.demo import seed_demo
from app.services.trends import get_price_trend


def test_demo_trend_is_explicit_and_has_seven_days(db):
    product = seed_demo(db)
    result = get_price_trend(db, product.id, date.today() - timedelta(days=6), date.today(), mode="demo")
    assert result["mode"] == "demo"
    assert result["source_label"] == "Demo 历史数据"
    assert len(result["daily"]) == 7
    assert result["summary"]["market_data_days"] == 7
    assert "Demo" in result["notice"]


def test_real_trend_uses_pdd_snapshots_only(db):
    product = Product(name="x", sku="X", cost=10, current_price=30, min_margin_rate=.2, stock=10)
    db.add(product)
    db.flush()
    competitor = Competitor(product_id=product.id, name="pdd", source_type="pdd_ddk", active=False)
    db.add(competitor)
    db.flush()
    first_day = date.today() - timedelta(days=1)
    db.add_all([
        CompetitorPriceSnapshot(competitor_id=competitor.id, price=20, sales=100, success=True, collected_at=datetime.combine(first_day, datetime.min.time()).replace(hour=12)),
        CompetitorPriceSnapshot(competitor_id=competitor.id, price=22, sales=110, success=True, collected_at=datetime.combine(date.today(), datetime.min.time()).replace(hour=12)),
    ])
    db.commit()

    result = get_price_trend(db, product.id, first_day, date.today(), mode="real")
    assert result["summary"]["market_data_days"] == 2
    assert result["summary"]["trend"] == "up"
    assert result["summary"]["trend_percent"] == 10.0
