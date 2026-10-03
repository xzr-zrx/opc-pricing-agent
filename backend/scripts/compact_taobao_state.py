import json
from pathlib import Path

src = Path("data/taobao_profile/storage_state.json")
dst = Path("data/taobao_profile/storage_state_compact.json")

with src.open("r", encoding="utf-8") as f:
    state = json.load(f)

keep_domains = (
    "taobao.com",
    "tmall.com",
    "alibaba.com",
    "alipay.com",
)

cookies = [
    cookie
    for cookie in state.get("cookies", [])
    if any(domain in cookie.get("domain", "") for domain in keep_domains)
]

compact = {
    "cookies": cookies,
    "origins": []
}

with dst.open("w", encoding="utf-8") as f:
    json.dump(
        compact,
        f,
        ensure_ascii=False,
        separators=(",", ":")
    )

print(f"cookies: {len(cookies)}")
print("origins: 0")
print(f"output: {dst}")
print(f"size: {dst.stat().st_size} bytes")