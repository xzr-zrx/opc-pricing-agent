from pathlib import Path
from playwright.sync_api import sync_playwright

state_path = Path("data/taobao_profile/storage_state_compact.json")

print("登录状态文件：", state_path.resolve())
print("文件是否存在：", state_path.exists())

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(
        storage_state=str(state_path)
    )

    page = context.new_page()

    print("正在打开淘宝...")

    try:
        page.goto(
            "https://www.taobao.com/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("当前网址：", page.url)
        print("页面标题：", page.title())

    except Exception as e:
        print("打开淘宝失败：")
        print(repr(e))

    input("请检查浏览器中淘宝是否已经登录，然后按 Enter 关闭...")

    browser.close()