import hashlib
import json
import os
import time

import httpx


API_URL = "https://gw-api.pinduoduo.com/api/router"


def sign(params: dict, secret: str) -> str:
    pieces = []
    for key in sorted(params):
        value = params[key]
        if value is None:
            continue
        pieces.append(f"{key}{value}")
    raw = f"{secret}{''.join(pieces)}{secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def call_pdd(method: str, extra: dict):
    client_id = os.getenv("PDD_CLIENT_ID", "").strip()
    secret = os.getenv("PDD_CLIENT_SECRET", "").strip()

    if not client_id or not secret:
        raise RuntimeError("请先设置 PDD_CLIENT_ID 和 PDD_CLIENT_SECRET")

    params = {
        "type": method,
        "client_id": client_id,
        "timestamp": int(time.time()),
        "data_type": "JSON",
        **extra,
    }

    params["sign"] = sign(params, secret)

    response = httpx.post(
        API_URL,
        data={k: str(v) for k, v in params.items()},
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


if __name__ == "__main__":
    pid = os.getenv("PDD_PID", "").strip()

    if not pid:
        raise RuntimeError("请先设置 PDD_PID")

    print("=== 生成备案链接 ===")

    print("=== 查询备案状态 ===")

    call_pdd(
        "pdd.ddk.member.authority.query",
        {
            "pid": pid,
        },
    )