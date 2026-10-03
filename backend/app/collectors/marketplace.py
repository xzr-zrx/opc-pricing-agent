from __future__ import annotations

import re
from dataclasses import dataclass

import httpx


SERPER_SHOPPING_URL = "https://google.serper.dev/shopping"
FRANKFURTER_USD_CNY_URL = "https://api.frankfurter.dev/v2/rate/usd/cny"


@dataclass(slots=True)
class MarketplaceItem:
    title: str
    price_cny: float
    popularity: int
    popularity_text: str
    shop_name: str | None
    url: str
    image_url: str | None
    rating: float | None
    original_price_text: str
    source: str = "google_shopping"


@dataclass(slots=True)
class MarketplaceSearchResult:
    items: list[MarketplaceItem]
    scanned_count: int
    valid_count: int
    usd_cny_rate: float | None


class MarketplaceCollectorError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _parse_price_text(text: str | None) -> tuple[float, str] | None:
    """解析 Google Shopping 的价格文本。

    当前比赛 MVP 只接受人民币或美元报价：
    - 人民币直接使用；
    - 美元使用公开汇率换算为人民币；
    - 其他币种跳过，避免把不同币种直接拿来做定价比较。
    """
    if not text:
        return None

    raw = str(text).strip()
    compact = raw.replace("\u00a0", " ")

    currency = None
    if re.search(r"(?:CN¥|CNY|￥|¥)", compact, re.IGNORECASE):
        currency = "CNY"
    elif re.search(r"(?:US\$|USD)", compact, re.IGNORECASE):
        currency = "USD"
    elif "$" in compact and not re.search(r"(?:R\$|A\$|C\$|HK\$|S\$)", compact, re.IGNORECASE):
        currency = "USD"

    if not currency:
        return None

    number = re.search(r"(\d[\d,]*(?:\.\d{1,2})?)", compact)
    if not number:
        return None

    try:
        value = float(number.group(1).replace(",", ""))
    except ValueError:
        return None

    if value <= 0:
        return None
    return value, currency


def _format_popularity(value: int) -> str:
    if value >= 10000:
        return f"{value / 10000:.1f}万条评价".replace(".0万", "万")
    if value >= 1000:
        return f"{value / 1000:.1f}千条评价".replace(".0千", "千")
    return f"{value}条评价"


async def _fetch_usd_cny_rate(client: httpx.AsyncClient) -> float:
    try:
        response = await client.get(FRANKFURTER_USD_CNY_URL)
        response.raise_for_status()
        payload = response.json()
        rate = float(payload.get("rate") or 0)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise MarketplaceCollectorError(
            "FX_RATE_UNAVAILABLE",
            "美元报价换算人民币所需的公开汇率暂时不可用，请稍后重试。",
            502,
        ) from exc

    if rate <= 0:
        raise MarketplaceCollectorError(
            "FX_RATE_UNAVAILABLE",
            "公开汇率接口未返回有效的美元兑人民币汇率。",
            502,
        )
    return rate


async def search_marketplace(
    keyword: str,
    api_key: str,
    timeout_seconds: int = 15,
    country: str = "us",
    language: str = "en",
    max_scan_items: int = 20,
) -> MarketplaceSearchResult:
    """通过 Serper Google Shopping 查询真实电商商品。

    Top5 以 ratingCount（公开评论/评分数量）作为“市场热度”排序指标，
    明确不是销量。价格统一换算为人民币后再入库，避免币种混用。
    """
    token = (api_key or "").strip()
    if not token:
        raise MarketplaceCollectorError(
            "SERPER_API_KEY_MISSING",
            "尚未配置电商竞品查询 API Key，请在 Render 后端环境变量中设置 SERPER_API_KEY。",
            428,
        )

    timeout = httpx.Timeout(max(5, timeout_seconds))
    headers = {
        "X-API-KEY": token,
        "Content-Type": "application/json",
    }
    body = {
        "q": keyword,
        "gl": country,
        "hl": language,
        "num": min(max(max_scan_items, 5), 100),
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.post(SERPER_SHOPPING_URL, headers=headers, json=body)

            if response.status_code in {401, 403}:
                raise MarketplaceCollectorError(
                    "SERPER_AUTH_FAILED",
                    "电商竞品查询 API Key 无效或没有访问权限，请检查 Render 中的 SERPER_API_KEY。",
                    502,
                )
            if response.status_code == 429:
                raise MarketplaceCollectorError(
                    "SERPER_QUOTA_EXHAUSTED",
                    "免费电商查询额度已用完或请求过于频繁，请稍后重试或检查 Serper 额度。",
                    429,
                )
            response.raise_for_status()
            payload = response.json()
            raw_items = payload.get("shopping") or []
            if not isinstance(raw_items, list):
                raw_items = []

            if not raw_items:
                raise MarketplaceCollectorError(
                    "MARKETPLACE_NO_RESULTS",
                    "未获取到有效的 Google Shopping 竞品结果，请更换关键词后重试。",
                    404,
                )

            # 只有确实遇到美元报价时才请求一次公开汇率。
            parsed_prices = [_parse_price_text(row.get("price")) for row in raw_items[:max_scan_items]]
            need_usd_rate = any(parsed and parsed[1] == "USD" for parsed in parsed_prices)
            usd_cny_rate = await _fetch_usd_cny_rate(client) if need_usd_rate else None

    except MarketplaceCollectorError:
        raise
    except httpx.TimeoutException as exc:
        raise MarketplaceCollectorError(
            "MARKETPLACE_TIMEOUT",
            "电商竞品查询超时，请稍后重试。",
            504,
        ) from exc
    except httpx.HTTPError as exc:
        raise MarketplaceCollectorError(
            "MARKETPLACE_ACCESS_FAILED",
            "电商竞品查询服务访问失败，请稍后重试。",
            502,
        ) from exc
    except (ValueError, TypeError) as exc:
        raise MarketplaceCollectorError(
            "MARKETPLACE_RESPONSE_INVALID",
            "电商竞品查询服务返回了无法解析的数据。",
            502,
        ) from exc

    valid: list[MarketplaceItem] = []
    scan_rows = raw_items[:max_scan_items]
    for row, parsed in zip(scan_rows, parsed_prices):
        if not isinstance(row, dict) or not parsed:
            continue

        title = str(row.get("title") or "").strip()
        url = str(row.get("link") or "").strip()
        if not title or not url.startswith(("http://", "https://")):
            continue

        amount, currency = parsed
        if currency == "USD":
            if not usd_cny_rate:
                continue
            price_cny = round(amount * usd_cny_rate, 2)
        else:
            price_cny = round(amount, 2)

        rating_count_raw = row.get("ratingCount")
        try:
            popularity = max(0, int(rating_count_raw or 0))
        except (TypeError, ValueError):
            popularity = 0

        rating_raw = row.get("rating")
        try:
            rating = float(rating_raw) if rating_raw is not None else None
        except (TypeError, ValueError):
            rating = None

        image_url = str(row.get("imageUrl") or row.get("thumbnail") or "").strip() or None
        shop_name = str(row.get("source") or "").strip() or None

        valid.append(
            MarketplaceItem(
                title=title,
                price_cny=price_cny,
                popularity=popularity,
                popularity_text=_format_popularity(popularity),
                shop_name=shop_name,
                url=url,
                image_url=image_url,
                rating=rating,
                original_price_text=str(row.get("price") or "").strip(),
            )
        )

    if not valid:
        raise MarketplaceCollectorError(
            "MARKETPLACE_NO_VALID_COMPETITORS",
            "搜索结果中没有同时具备有效商品链接和可比较价格的竞品。",
            404,
        )

    # “热度 Top5”按评论/评分数量排序；评论数相同再按评分排序。
    valid.sort(key=lambda item: (item.popularity, item.rating or 0), reverse=True)
    top5 = valid[:5]

    return MarketplaceSearchResult(
        items=top5,
        scanned_count=len(scan_rows),
        valid_count=len(valid),
        usd_cny_rate=usd_cny_rate,
    )
