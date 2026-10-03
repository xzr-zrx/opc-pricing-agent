from __future__ import annotations

import base64
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TaobaoItem:
    title: str
    price: float
    sales: int
    sales_text: str
    shop_name: str | None
    url: str
    image_url: str | None
    source: str = "taobao"


@dataclass(slots=True)
class TaobaoSearchResult:
    items: list[TaobaoItem]
    scanned_count: int
    valid_count: int


class TaobaoCollectorError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def ensure_storage_state_file(storage_state_path: str, storage_state_b64: str | None = None) -> Path:
    """确保 Playwright storage state 文件存在。

    云端优先支持把 storage_state.json 的 Base64 内容放进环境变量；
    本地开发仍兼容直接读取磁盘上的 storage_state.json。
    """
    state_path = Path(storage_state_path)

    # 文件已存在时优先复用它。这样 Playwright 在运行期间刷新后的 cookie
    # 不会被每次请求都用旧环境变量覆盖。Render 重启/重新部署后文件会重新生成。
    if state_path.exists():
        return state_path

    encoded = (storage_state_b64 or "").strip()
    if not encoded:
        raise TaobaoCollectorError(
            "TAOBAO_LOGIN_REQUIRED",
            "尚未找到淘宝登录状态。请先本地登录淘宝，或在 Render 配置 TAOBAO_STORAGE_STATE_B64。",
            428,
        )

    try:
        raw = base64.b64decode(encoded, validate=True)
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise TaobaoCollectorError(
            "TAOBAO_STORAGE_STATE_INVALID",
            "Render 中的 TAOBAO_STORAGE_STATE_B64 无效，请重新生成并完整粘贴。",
            500,
        ) from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("cookies", []), list):
        raise TaobaoCollectorError(
            "TAOBAO_STORAGE_STATE_INVALID",
            "淘宝登录状态格式不正确，请重新生成 storage_state.json。",
            500,
        )

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = state_path.with_suffix(state_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(state_path)
    except OSError as exc:
        raise TaobaoCollectorError(
            "TAOBAO_STORAGE_STATE_WRITE_FAILED",
            "服务器无法创建淘宝登录状态临时文件，请检查运行目录写权限。",
            500,
        ) from exc

    return state_path


def parse_sales_text(text: str | None) -> int | None:
    """把淘宝页面展示销量统一转换为整数。

    支持：500+、1千+、2.3万+、10万+、1.2w、3k 等常见展示形式。
    返回 None 表示无法可靠解析。
    """
    if not text:
        return None
    cleaned = str(text).replace(",", "").replace("，", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(万|千|w|W|k|K)?\s*\+?", cleaned)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit in {"万", "w", "W"}:
        value *= 10000
    elif unit in {"千", "k", "K"}:
        value *= 1000
    return int(value)


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = str(text).replace(",", "").strip()
    currency = re.search(r"[¥￥]\s*(\d+(?:\.\d+)?)", cleaned)
    match = currency or re.search(r"\b(\d+(?:\.\d+)?)\b", cleaned)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return value if value > 0 else None


def _extract_sales_text(card_text: str | None, explicit_text: str | None = None) -> str | None:
    if explicit_text:
        direct = re.search(r"(\d+(?:\.\d+)?\s*(?:万|千|w|W|k|K)?\s*\+?)", explicit_text.replace(",", ""))
        if direct and parse_sales_text(direct.group(1)) is not None:
            return direct.group(1).replace(" ", "")

    candidates = [card_text or ""]
    patterns = [
        r"(?:已售|销量|月销|付款|人付款|人收货)\s*[:：]?\s*(\d+(?:\.\d+)?\s*(?:万|千|w|W|k|K)?\s*\+?)",
        r"(\d+(?:\.\d+)?\s*(?:万|千|w|W|k|K)?\s*\+?)\s*(?:人付款|人收货|已售)",
    ]
    for candidate in candidates:
        compact = re.sub(r"\s+", " ", candidate)
        for pattern in patterns:
            match = re.search(pattern, compact)
            if match:
                return match.group(1).replace(" ", "")
    return None


def _canonical_item_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    url = raw_url.strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = "https://s.taobao.com" + url
    if not url.startswith(("http://", "https://")):
        return None

    parsed = urlparse(url)
    if not (parsed.netloc.endswith("taobao.com") or parsed.netloc.endswith("tmall.com")):
        return None
    item_id = parse_qs(parsed.query).get("id", [None])[0]
    if item_id:
        scheme = "https"
        host = "detail.tmall.com" if "tmall.com" in parsed.netloc else "item.taobao.com"
        return f"{scheme}://{host}/item.htm?id={item_id}"
    return url


def _normalize_image_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    value = raw_url.strip()
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("http://"):
        return "https://" + value[len("http://"):]
    return value if value.startswith("https://") else None


def _looks_like_login_page(url: str, body_text: str) -> bool:
    lower = url.lower()
    if any(part in lower for part in ("login.taobao.com", "passport.taobao.com", "login.tmall.com")):
        return True
    text = body_text.replace(" ", "")
    return "登录后查看更多" in text or "请先登录" in text or "亲，请登录" in text


def _looks_like_verification_page(url: str, body_text: str) -> bool:
    lower = url.lower()
    text = body_text.replace(" ", "")
    url_hit = any(part in lower for part in ("verify", "sec.taobao", "punish", "captcha"))
    text_hit = any(word in text for word in ("安全验证", "滑动验证", "请完成验证", "验证码", "访问异常"))
    return url_hit or text_hit


async def search_taobao(
    keyword: str,
    storage_state_path: str,
    storage_state_b64: str | None = None,
    timeout_seconds: int = 35,
    max_scan_items: int = 60,
    headless: bool = True,
) -> TaobaoSearchResult:
    state_path = ensure_storage_state_file(storage_state_path, storage_state_b64)

    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise TaobaoCollectorError(
            "PLAYWRIGHT_NOT_INSTALLED",
            "后端未安装 Playwright，请重新构建后端镜像或安装 requirements.txt。",
            500,
        ) from exc

    timeout_ms = max(5, timeout_seconds) * 1000
    search_url = f"https://s.taobao.com/search?q={quote(keyword)}&sort=_sale-desc"

    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
            except PlaywrightError as exc:
                message = str(exc)
                code = "PLAYWRIGHT_BROWSER_MISSING" if "Executable doesn't exist" in message else "TAOBAO_BROWSER_START_FAILED"
                readable = (
                    "Playwright Chromium 不存在，请执行 python -m playwright install chromium，或重新构建 Docker 后端镜像。"
                    if code == "PLAYWRIGHT_BROWSER_MISSING"
                    else "淘宝采集浏览器启动失败，请检查 Playwright/Chromium 运行依赖。"
                )
                raise TaobaoCollectorError(code, readable, 500) from exc

            context = await browser.new_context(
                storage_state=str(state_path),
                locale="zh-CN",
                viewport={"width": 1440, "height": 1000},
            )

            # 竞品查询只依赖 DOM 文本和链接。Render 免费实例上不下载图片、字体、
            # 音视频，可显著减少网络流量和 Chromium 资源占用。
            async def block_heavy_resources(route):
                if route.request.resource_type in {"image", "media", "font"}:
                    await route.abort()
                else:
                    await route.continue_()

            await context.route("**/*", block_heavy_resources)
            page = await context.new_page()
            page.set_default_timeout(timeout_ms)

            started_at = time.perf_counter()
            logger.info("[Taobao] start keyword=%s", keyword)

            try:
                # 只等到服务器开始返回页面，不再等待淘宝整页 DOMContentLoaded。
                # 淘宝页面资源很多，Render 海外实例等待完整首屏会明显变慢。
                await page.goto(
                    search_url,
                    wait_until="commit",
                    timeout=min(timeout_ms, 30000),
                )
                logger.info(
                    "[Taobao] page connected %.2fs url=%s",
                    time.perf_counter() - started_at,
                    page.url,
                )

                link_selector = (
                    'a[href*="item.taobao.com/item.htm"], '
                    'a[href*="detail.tmall.com/item.htm"]'
                )

                # 不等整张淘宝页面完全加载，只等待商品链接进入 DOM。
                try:
                    await page.wait_for_selector(
                        link_selector,
                        state="attached",
                        timeout=min(timeout_ms, 45000),
                    )
                except PlaywrightTimeoutError:
                    # 后面继续读取 body，以区分登录失效、验证码、风控和真正无结果。
                    pass

                logger.info(
                    "[Taobao] product wait finished %.2fs",
                    time.perf_counter() - started_at,
                )

                # 给淘宝前端少量时间完成首屏渲染，再轻量滚动加载更多商品。
                await page.wait_for_timeout(800)
                for _ in range(2):
                    await page.evaluate("window.scrollBy(0, 900)")
                    await page.wait_for_timeout(250)

                logger.info(
                    "[Taobao] scrolling finished %.2fs",
                    time.perf_counter() - started_at,
                )

                body_text = (await page.locator("body").inner_text(timeout=5000))[:20000]
                current_url = page.url
                link_count = await page.locator(link_selector).count()
                verification_dom = await page.locator(
                    '.nc-container, [id*="nc_"][class*="nc"], [class*="baxia"], [class*="Captcha"]'
                ).count()

                if link_count == 0 and (verification_dom > 0 or _looks_like_verification_page(current_url, body_text)):
                    raise TaobaoCollectorError(
                        "TAOBAO_VERIFICATION_REQUIRED",
                        "淘宝要求安全验证/验证码，请在本机浏览器重新完成验证后再查询。",
                        428,
                    )
                if link_count == 0 and _looks_like_login_page(current_url, body_text):
                    raise TaobaoCollectorError(
                        "TAOBAO_LOGIN_REQUIRED",
                        "淘宝登录状态已失效，请重新完成登录。",
                        428,
                    )

                raw_items = await page.evaluate(
                    """
                    (maxItems) => {
                      const links = Array.from(document.querySelectorAll(
                        'a[href*="item.taobao.com/item.htm"], a[href*="detail.tmall.com/item.htm"]'
                      ));
                      const seen = new Set();
                      const rows = [];

                      function pickText(root, selectors) {
                        for (const selector of selectors) {
                          const el = root.querySelector(selector);
                          const text = (el?.innerText || el?.textContent || '').trim();
                          if (text) return text;
                        }
                        return '';
                      }

                      function findCard(anchor) {
                        let node = anchor;
                        let best = anchor.parentElement || anchor;
                        for (let i = 0; i < 8 && node; i += 1, node = node.parentElement) {
                          const text = (node.innerText || '').trim();
                          if (text.length >= 20 && text.length <= 1200 && node.querySelector('img')) {
                            best = node;
                            if (/¥|￥|已售|付款|销量|月销/.test(text)) return node;
                          }
                        }
                        return best;
                      }

                      for (const anchor of links) {
                        if (rows.length >= maxItems) break;
                        const href = anchor.href || anchor.getAttribute('href') || '';
                        if (!href || seen.has(href)) continue;
                        seen.add(href);

                        const card = findCard(anchor);
                        const cardText = (card.innerText || '').trim();
                        const titleEl = card.querySelector(
                          '[class*="Title--"], [class*="title"], a[title]'
                        );
                        const title = (
                          titleEl?.getAttribute('title') || titleEl?.innerText ||
                          anchor.getAttribute('title') || anchor.innerText || ''
                        ).trim();
                        const priceText = pickText(card, [
                          '[class*="Price--"]', '[class*="price"]', '[class*="Price"]'
                        ]);
                        const salesText = pickText(card, [
                          '[class*="Deal--"]', '[class*="Sales--"]', '[class*="Sale--"]',
                          '[class*="sales"]', '[class*="sale"]', '[class*="realSales"]',
                          '[class*="sell"]', '[class*="trade"]'
                        ]);
                        const shopText = pickText(card, [
                          '[class*="ShopInfo--shopName"]', '[class*="shopName"]',
                          '[class*="Shop"] a', 'a[href*="shop"]'
                        ]);
                        const img = card.querySelector('img');
                        const imageUrl = img?.src || img?.getAttribute('data-src') || img?.getAttribute('data-ks-lazyload') || '';
                        rows.push({ href, title, priceText, salesText, shopText, imageUrl, cardText });
                      }
                      return rows;
                    }
                    """,
                    max_scan_items,
                )

                logger.info(
                    "[Taobao] DOM parsed %.2fs raw_items=%d",
                    time.perf_counter() - started_at,
                    len(raw_items),
                )

                # 本地 storage_state 可刷新 cookie；Render Secret File 位于 /etc/secrets，
                # 运行时只读，不能写回，否则一次成功查询也可能因为权限错误最终失败。
                if not str(state_path).startswith("/etc/secrets/"):
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    await context.storage_state(path=str(state_path))
                else:
                    logger.info("[Taobao] skip storage-state writeback for Render secret file")
            finally:
                await context.close()
                await browser.close()

    except TaobaoCollectorError:
        raise
    except PlaywrightTimeoutError as exc:
        raise TaobaoCollectorError("TAOBAO_TIMEOUT", "淘宝查询超时，请检查网络后稍后重试。", 504) from exc
    except PlaywrightError as exc:
        raise TaobaoCollectorError("TAOBAO_ACCESS_FAILED", "淘宝页面访问失败，请稍后重试。", 502) from exc
    except OSError as exc:
        raise TaobaoCollectorError("TAOBAO_ACCESS_FAILED", "淘宝页面访问失败，请检查网络和登录状态。", 502) from exc

    items: list[TaobaoItem] = []
    seen_urls: set[str] = set()
    for raw in raw_items:
        url = _canonical_item_url(raw.get("href"))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        price = _parse_price(raw.get("priceText"))
        if price is None:
            card_text = raw.get("cardText") or ""
            currency = re.search(r"[¥￥]\s*(\d+(?:\.\d+)?)", card_text.replace(",", ""))
            price = float(currency.group(1)) if currency else None
        sales_text = _extract_sales_text(raw.get("cardText"), raw.get("salesText"))
        sales = parse_sales_text(sales_text)
        title = (raw.get("title") or "").strip()

        if not title:
            # DOM 类名变化时仍尽量从卡片文本取第一行作为标题，但不伪造字段。
            title = next((line.strip() for line in (raw.get("cardText") or "").splitlines() if len(line.strip()) >= 4), "")

        if not title or price is None or sales is None:
            continue

        items.append(
            TaobaoItem(
                title=title[:120],
                price=round(price, 2),
                sales=sales,
                sales_text=sales_text or str(sales),
                shop_name=(raw.get("shopText") or "").strip()[:160] or None,
                url=url,
                image_url=_normalize_image_url(raw.get("imageUrl")),
            )
        )

    valid_count = len(items)
    if not raw_items:
        raise TaobaoCollectorError(
            "TAOBAO_NO_RESULTS",
            "未获取到淘宝搜索结果，可能是页面结构变化、登录失效或当前关键词没有结果。",
            502,
        )
    if valid_count == 0:
        raise TaobaoCollectorError(
            "TAOBAO_NO_VALID_COMPETITORS",
            "本次未获取到同时包含价格和销量的有效竞品，请检查淘宝页面或重新登录。",
            422,
        )

    items.sort(key=lambda item: item.sales, reverse=True)
    return TaobaoSearchResult(items=items[:5], scanned_count=len(raw_items), valid_count=valid_count)
