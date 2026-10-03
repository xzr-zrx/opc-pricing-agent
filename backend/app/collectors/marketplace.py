from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass

import httpx


PDD_API_URL = "https://gw-api.pinduoduo.com/api/router"
PDD_SEARCH_METHOD = "pdd.ddk.goods.search"


@dataclass(slots=True)
class MarketplaceItem:
    title: str
    price_cny: float
    sales: int
    sales_text: str
    shop_name: str | None
    url: str
    image_url: str | None
    goods_id: str
    goods_sign: str | None
    original_price_cents: int | None
    source: str = "pdd_ddk"


@dataclass(slots=True)
class MarketplaceSearchResult:
    items: list[MarketplaceItem]
    scanned_count: int
    valid_count: int
    request_id: str | None
    search_id: str | None


class MarketplaceCollectorError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _normalize_param_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _build_sign(params: dict[str, object], client_secret: str) -> str:
    """按拼多多开放平台通用规则生成 MD5 大写签名。"""
    pieces = []
    for key in sorted(params):
        value = params[key]
        if value is None:
            continue
        pieces.append(f"{key}{_normalize_param_value(value)}")
    raw = f"{client_secret}{''.join(pieces)}{client_secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def _parse_sales_text(text: str | None) -> int | None:
    """把平台展示销量文本转为可排序整数。

    支持示例：500、500+、1千+、2.3万+、10万+、已拼4452件、全店总售500万+件。
    该值仅代表接口返回的 sales_tip 所表达的销量口径。
    """
    if text is None:
        return None
    raw = str(text).strip().replace(",", "")
    if not raw:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*([千千万亿]?)", raw)
    if not match:
        return None

    try:
        number = float(match.group(1))
    except ValueError:
        return None

    unit = match.group(2)
    multiplier = {"": 1, "千": 1_000, "万": 10_000, "亿": 100_000_000}.get(unit, 1)
    value = int(number * multiplier)
    return max(value, 0)


def _display_sales_text(raw_text: str | None, value: int) -> str:
    raw = str(raw_text or "").strip()
    if raw:
        return raw
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f}亿+".replace(".0亿", "亿")
    if value >= 10_000:
        return f"{value / 10_000:.1f}万+".replace(".0万", "万")
    if value >= 1_000:
        return f"{value / 1_000:.1f}千+".replace(".0千", "千")
    return str(value)


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def search_marketplace(
    keyword: str,
    client_id: str,
    client_secret: str,
    pid: str,
    custom_parameters: str = "",
    timeout_seconds: int = 15,
    max_scan_items: int = 50,
) -> MarketplaceSearchResult:
    """通过拼多多多多进宝官方商品搜索接口查询真实竞品。

    请求使用 pdd.ddk.goods.search，并要求平台按销量降序返回；服务端仍会
    对成功解析出的 sales_tip 再排序一次，最终只返回当前搜索结果中的 Top5。
    """
    app_id = (client_id or "").strip()
    secret = (client_secret or "").strip()
    if not app_id or not secret:
        raise MarketplaceCollectorError(
            "PDD_CREDENTIALS_MISSING",
            "尚未配置拼多多开放平台凭证，请在 Render 后端环境变量中设置 PDD_CLIENT_ID 和 PDD_CLIENT_SECRET。",
            428,
        )

    pdd_pid = (pid or "").strip()
    if not pdd_pid:
        raise MarketplaceCollectorError(
            "PDD_PID_MISSING",
            "尚未配置已备案的拼多多推广位 PID，请在 Render 后端环境变量中设置 PDD_PID。",
            428,
        )

    page_size = min(max(max_scan_items, 5), 100)
    params: dict[str, object] = {
        "type": PDD_SEARCH_METHOD,
        "client_id": app_id,
        "timestamp": int(time.time()),
        "data_type": "JSON",
        "keyword": keyword,
        "pid": pdd_pid,
        "page": 1,
        "page_size": page_size,
        # 官方多多进宝商品搜索排序：6 表示按销量降序。
        "sort_type": 6,
        "with_coupon": False,
    }
    custom = (custom_parameters or "").strip()
    if custom:
        # 必须与多多进宝授权备案时使用的 custom_parameters 保持一致。
        params["custom_parameters"] = custom
    params["sign"] = _build_sign(params, secret)
    form_data = {key: _normalize_param_value(value) for key, value in params.items()}

    try:
        timeout = httpx.Timeout(max(5, timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.post(PDD_API_URL, data=form_data)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise MarketplaceCollectorError(
            "PDD_TIMEOUT",
            "拼多多商品查询超时，请稍后重试。",
            504,
        ) from exc
    except httpx.HTTPError as exc:
        raise MarketplaceCollectorError(
            "PDD_ACCESS_FAILED",
            "拼多多开放平台访问失败，请稍后重试。",
            502,
        ) from exc
    except (ValueError, TypeError) as exc:
        raise MarketplaceCollectorError(
            "PDD_RESPONSE_INVALID",
            "拼多多开放平台返回了无法解析的数据。",
            502,
        ) from exc

    error_response = payload.get("error_response") if isinstance(payload, dict) else None
    if isinstance(error_response, dict):
        error_code = error_response.get("error_code")
        error_msg = str(error_response.get("sub_msg") or error_response.get("error_msg") or "接口调用失败")
        # 不把 client_secret 等请求内容写进错误信息。
        raise MarketplaceCollectorError(
            "PDD_API_ERROR",
            f"拼多多开放平台返回错误（{error_code}）：{error_msg}",
            502,
        )

    container = payload.get("goods_search_response") if isinstance(payload, dict) else None
    if not isinstance(container, dict):
        raise MarketplaceCollectorError(
            "PDD_RESPONSE_INVALID",
            "拼多多开放平台未返回商品搜索结果。",
            502,
        )

    raw_items = container.get("goods_list") or []
    if not isinstance(raw_items, list) or not raw_items:
        raise MarketplaceCollectorError(
            "MARKETPLACE_NO_RESULTS",
            "未获取到有效的拼多多竞品结果，请更换关键词后重试。",
            404,
        )

    valid: list[MarketplaceItem] = []
    scan_rows = raw_items[:page_size]
    for row in scan_rows:
        if not isinstance(row, dict):
            continue

        title = str(row.get("goods_name") or "").strip()
        goods_id_raw = row.get("goods_id")
        goods_id = str(goods_id_raw or "").strip()
        sales_text_raw = str(row.get("sales_tip") or "").strip()
        sales = _parse_sales_text(sales_text_raw)

        group_price_cents = _safe_int(row.get("min_group_price"))
        normal_price_cents = _safe_int(row.get("min_normal_price"))
        price_cents = group_price_cents or normal_price_cents

        # Top5 只使用成功解析到标题、价格、销量和可点击商品 ID 的结果。
        if not title or not goods_id or not price_cents or price_cents <= 0 or sales is None:
            continue

        shop_name = str(row.get("mall_name") or "").strip() or None
        image_url = str(row.get("goods_thumbnail_url") or row.get("goods_image_url") or "").strip() or None
        goods_sign = str(row.get("goods_sign") or "").strip() or None
        url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"

        valid.append(
            MarketplaceItem(
                title=title,
                price_cny=round(price_cents / 100, 2),
                sales=sales,
                sales_text=_display_sales_text(sales_text_raw, sales),
                shop_name=shop_name,
                url=url,
                image_url=image_url,
                goods_id=goods_id,
                goods_sign=goods_sign,
                original_price_cents=normal_price_cents,
            )
        )

    if not valid:
        raise MarketplaceCollectorError(
            "MARKETPLACE_NO_VALID_COMPETITORS",
            "搜索结果中没有同时具备有效价格、销量和商品链接的竞品。",
            404,
        )

    valid.sort(key=lambda item: item.sales, reverse=True)
    top5 = valid[:5]

    return MarketplaceSearchResult(
        items=top5,
        scanned_count=len(scan_rows),
        valid_count=len(valid),
        request_id=str(container.get("request_id") or "").strip() or None,
        search_id=str(container.get("search_id") or "").strip() or None,
    )
