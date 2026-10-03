import asyncio

from app.collectors.marketplace import MarketplaceItem, MarketplaceSearchResult, _format_popularity, _parse_price_text
from app.models import Competitor, Product
from app.services import marketplace as marketplace_service
from app.tools.pricing_tools import get_competitor_context


def test_marketplace_price_parser_and_popularity_format():
    assert _parse_price_text("$19.99") == (19.99, "USD")
    assert _parse_price_text("US$ 1,299.00") == (1299.0, "USD")
    assert _parse_price_text("¥59.90") == (59.9, "CNY")
    assert _parse_price_text("R$ 59,90") is None
    assert _format_popularity(23000) == "2.3万条评价"
    assert _format_popularity(1200) == "1.2千条评价"


def test_marketplace_store_and_agent_context(db, monkeypatch):
    p = Product(
        name="bear",
        sku="BEAR",
        search_keyword="personalized graduation teddy bear",
        cost=22,
        current_price=59,
        min_margin_rate=.3,
        stock=10,
    )
    db.add(p)
    db.flush()

    old = Competitor(
        product_id=p.id,
        name="old",
        source_type="google_shopping",
        url="https://example.com/old",
        active=True,
    )
    db.add(old)
    db.commit()

    async def fake_search(**_kwargs):
        return MarketplaceSearchResult(
            items=[
                MarketplaceItem(
                    title="Bear A",
                    price_cny=48.8,
                    popularity=2300,
                    popularity_text="2.3千条评价",
                    shop_name="Shop A",
                    url="https://example.com/a",
                    image_url=None,
                    rating=4.8,
                    original_price_text="$6.88",
                ),
                MarketplaceItem(
                    title="Bear B",
                    price_cny=55.0,
                    popularity=1200,
                    popularity_text="1.2千条评价",
                    shop_name="Shop B",
                    url="https://example.com/b",
                    image_url=None,
                    rating=4.6,
                    original_price_text="$7.75",
                ),
            ],
            scanned_count=10,
            valid_count=8,
            usd_cny_rate=7.09,
        )

    monkeypatch.setattr(marketplace_service, "search_marketplace", fake_search)
    payload = asyncio.run(marketplace_service.search_and_store_marketplace(db, p.id))

    assert payload["count"] == 2
    assert payload["items"][0]["popularity"] == 2300
    assert payload["source"] == "google_shopping"
    db.refresh(old)
    assert old.active is False

    agent_data = get_competitor_context(db, p.id)
    assert agent_data["data_source"] == "google_shopping_manual_top5"
    assert agent_data["competitors"][0]["popularity_count"] == 2300
    assert "不是销量" in agent_data["popularity_note"]
