import base64
import json

from app.collectors.taobao import TaobaoCollectorError, ensure_storage_state_file, parse_sales_text
from app.models import Competitor, CompetitorPriceSnapshot, Product
from app.tools.pricing_tools import get_competitor_context


def test_parse_sales_text():
    assert parse_sales_text("500+") == 500
    assert parse_sales_text("1千+") == 1000
    assert parse_sales_text("2.3万+") == 23000
    assert parse_sales_text("10万+") == 100000
    assert parse_sales_text("1.2w") == 12000
    assert parse_sales_text(None) is None


def test_storage_state_can_be_materialized_from_base64(tmp_path):
    payload = {"cookies": [{"name": "cookie2", "value": "demo"}], "origins": []}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    target = tmp_path / "taobao" / "storage_state.json"

    result = ensure_storage_state_file(str(target), encoded)

    assert result == target
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_storage_state_invalid_base64_is_rejected(tmp_path):
    target = tmp_path / "storage_state.json"
    try:
        ensure_storage_state_file(str(target), "not-valid-base64@@")
    except TaobaoCollectorError as exc:
        assert exc.code == "TAOBAO_STORAGE_STATE_INVALID"
    else:
        raise AssertionError("invalid Base64 should be rejected")


def test_agent_prefers_active_taobao_top5(db):
    p = Product(name="x", sku="X", cost=10, current_price=30, min_margin_rate=.2, stock=10)
    db.add(p)
    db.flush()

    mock = Competitor(product_id=p.id, name="mock", source_type="mock", active=True)
    tb = Competitor(product_id=p.id, name="taobao item", source_type="taobao", url="https://item.taobao.com/item.htm?id=1", active=True)
    db.add_all([mock, tb])
    db.flush()
    db.add(CompetitorPriceSnapshot(competitor_id=mock.id, price=29, success=True))
    db.add(CompetitorPriceSnapshot(competitor_id=tb.id, price=25, sales=2300, sales_text="2300+", success=True))
    db.commit()

    data = get_competitor_context(db, p.id)
    assert data["data_source"] == "taobao_manual_top5"
    assert len(data["competitors"]) == 1
    assert data["competitors"][0]["sales"] == 2300
    assert data["competitors"][0]["current_price"] == 25

import asyncio
from app.collectors.taobao import TaobaoItem, TaobaoSearchResult
from app.services import taobao as taobao_service


def test_search_and_store_replaces_current_taobao_set(db, monkeypatch):
    p = Product(name="bear", sku="BEAR", search_keyword="毕业小熊 定制", cost=22, current_price=59, min_margin_rate=.3, stock=10)
    db.add(p)
    db.flush()
    old = Competitor(product_id=p.id, name="old", source_type="taobao", url="https://item.taobao.com/item.htm?id=old", active=True)
    db.add(old)
    db.commit()

    async def fake_search(**_kwargs):
        return TaobaoSearchResult(
            items=[
                TaobaoItem("A", 39.9, 23000, "2.3万+", "店A", "https://item.taobao.com/item.htm?id=1", None),
                TaobaoItem("B", 45.0, 18000, "1.8万+", "店B", "https://item.taobao.com/item.htm?id=2", None),
            ],
            scanned_count=20,
            valid_count=12,
        )

    monkeypatch.setattr(taobao_service, "search_taobao", fake_search)
    payload = asyncio.run(taobao_service.search_and_store_taobao(db, p.id))
    assert payload["count"] == 2
    assert payload["items"][0]["sales"] == 23000
    db.refresh(old)
    assert old.active is False

    agent_data = get_competitor_context(db, p.id)
    assert agent_data["data_source"] == "taobao_manual_top5"
    assert [x["sales"] for x in agent_data["competitors"]] == [23000, 18000]
