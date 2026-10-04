import asyncio
import hashlib

from app.collectors.marketplace import (
    MarketplaceItem,
    MarketplaceSearchResult,
    _build_sign,
    _parse_sales_text,
)
from app.models import Competitor, Product
from app.services import marketplace as marketplace_service
from app.tools.pricing_tools import get_competitor_context


def test_pdd_sales_parser_and_sign():
    assert _parse_sales_text("500+") == 500
    assert _parse_sales_text("1千+") == 1000
    assert _parse_sales_text("2.3万+") == 23000
    assert _parse_sales_text("10万+") == 100000
    assert _parse_sales_text("已拼4452件") == 4452
    assert _parse_sales_text("全店总售500万+件") == 5_000_000

    params = {
        "client_id": "abc",
        "data_type": "JSON",
        "keyword": "毕业小熊 定制",
        "timestamp": 1234567890,
        "type": "pdd.ddk.goods.search",
    }
    secret = "xyz"
    raw = secret + "".join(f"{k}{params[k]}" for k in sorted(params)) + secret
    expected = hashlib.md5(raw.encode("utf-8")).hexdigest().upper()
    assert _build_sign(params, secret) == expected


def test_marketplace_store_and_agent_context(db, monkeypatch):
    p = Product(
        name="bear",
        sku="BEAR",
        search_keyword="毕业小熊 定制",
        cost=22,
        current_price=59,
        min_margin_rate=.3,
        stock=10,
    )
    db.add(p)
    db.flush()

    old = Competitor(
        product_id=p.id,
        name="old google result",
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
                    title="毕业小熊 A",
                    price_cny=39.9,
                    sales=23000,
                    sales_text="2.3万+",
                    shop_name="店铺 A",
                    url="https://mobile.yangkeduo.com/goods.html?goods_id=1001",
                    image_url=None,
                    goods_id="1001",
                    goods_sign="sign-a",
                    original_price_cents=4590,
                ),
                MarketplaceItem(
                    title="毕业小熊 B",
                    price_cny=45.0,
                    sales=18000,
                    sales_text="1.8万+",
                    shop_name="店铺 B",
                    url="https://mobile.yangkeduo.com/goods.html?goods_id=1002",
                    image_url=None,
                    goods_id="1002",
                    goods_sign="sign-b",
                    original_price_cents=4990,
                ),
            ],
            scanned_count=20,
            valid_count=8,
            request_id="req-1",
            search_id="search-1",
        )

    monkeypatch.setattr(marketplace_service, "search_marketplace", fake_search)
    payload = asyncio.run(marketplace_service.search_and_store_marketplace(db, p.id))

    assert payload["count"] == 2
    assert payload["items"][0]["sales"] == 23000
    assert payload["source"] == "pdd_ddk"
    assert payload["provider_name"] == "拼多多 / 多多进宝"
    db.refresh(old)
    assert old.active is False

    agent_data = get_competitor_context(db, p.id)
    assert agent_data["data_source"] == "pdd_ddk_manual_top15"
    assert agent_data["competitors"][0]["sales"] == 23000
    assert "不代表拼多多全平台绝对销量" in agent_data["sales_note"]
