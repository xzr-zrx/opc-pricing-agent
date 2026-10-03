from __future__ import annotations
import json, re
import httpx
from bs4 import BeautifulSoup
from app.models import Competitor
from .base import CollectResult


def collect_mock(c: Competitor, advance: bool = False) -> CollectResult:
    prices = json.loads(c.mock_prices_json or "[]")
    promos = json.loads(c.mock_promos_json or "[]")
    if not prices:
        return CollectResult(False, None, error="mock price sequence empty")
    idx = c.mock_index
    if advance and idx < len(prices) - 1:
        idx += 1
        c.mock_index = idx
    price = float(prices[min(idx, len(prices)-1)])
    promo = promos[min(idx, len(promos)-1)] if promos else None
    return CollectResult(True, price, promo, raw=f"mock:{idx}:{price}:{promo}")


def collect_manual(c: Competitor, **_) -> CollectResult:
    if c.manual_price is None:
        return CollectResult(False, None, error="manual_price missing")
    return CollectResult(True, c.manual_price, c.manual_promo, raw=f"manual:{c.manual_price}:{c.manual_promo}")


def collect_generic_html(c: Competitor, **_) -> CollectResult:
    if not c.url or not c.price_selector:
        return CollectResult(False, None, error="url/price_selector missing")
    try:
        with httpx.Client(timeout=10, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0 OPC-Demo/1.0"}) as client:
            r = client.get(c.url)
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        price_el = soup.select_one(c.price_selector)
        if not price_el:
            return CollectResult(False, None, error="price selector not matched")
        match = re.search(r"\d+(?:\.\d+)?", price_el.get_text(" ", strip=True).replace(",", ""))
        if not match:
            return CollectResult(False, None, error="price not found")
        promo_el = soup.select_one(c.promo_selector) if c.promo_selector else None
        promo = promo_el.get_text(" ", strip=True) if promo_el else None
        return CollectResult(True, float(match.group()), promo, raw=r.text[:1000])
    except Exception as e:
        return CollectResult(False, None, error=str(e))


def collect(c: Competitor, advance: bool = False) -> CollectResult:
    if c.source_type == "mock":
        return collect_mock(c, advance=advance)
    if c.source_type == "manual":
        return collect_manual(c)
    if c.source_type == "generic_html":
        return collect_generic_html(c)
    return CollectResult(False, None, error=f"unsupported source_type: {c.source_type}")
