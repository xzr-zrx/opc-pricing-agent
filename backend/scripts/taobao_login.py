from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings


async def main() -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise SystemExit("未安装 Playwright。请先执行：pip install -r requirements.txt")

    settings = get_settings()
    state_path = Path(settings.taobao_storage_state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    print("即将打开 Playwright Chromium。请在浏览器中自行扫码/登录淘宝。")
    print("不要把淘宝账号密码写入代码或 .env。")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False)
        except Exception as exc:
            raise SystemExit(
                "Chromium 尚未安装。请先执行：python -m playwright install chromium\n"
                f"原始错误：{exc}"
            ) from exc

        context = await browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1000})
        page = await context.new_page()
        await page.goto("https://login.taobao.com/member/login.jhtml", wait_until="domcontentloaded")

        input("\n完成淘宝登录，并确认浏览器内可以正常访问淘宝搜索页后，回到终端按 Enter 保存登录状态... ")
        await context.storage_state(path=str(state_path))
        await context.close()
        await browser.close()

    encoded = base64.b64encode(state_path.read_bytes()).decode("ascii")
    render_value_path = state_path.parent / "render_taobao_storage_state_b64.txt"
    render_value_path.write_text(encoded, encoding="utf-8")

    print(f"登录状态已保存到：{state_path.resolve()}")
    print(f"Render 环境变量值已生成到：{render_value_path.resolve()}")
    print("Render 中新增环境变量：TAOBAO_STORAGE_STATE_B64")
    print("其 Value 请粘贴 render_taobao_storage_state_b64.txt 中完整的一整行内容。")
    print("注意：这两个文件都包含登录凭证，不要提交到 GitHub。")


if __name__ == "__main__":
    asyncio.run(main())
