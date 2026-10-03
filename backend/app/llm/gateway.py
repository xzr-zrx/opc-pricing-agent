from __future__ import annotations
import asyncio, json
from dataclasses import dataclass
from typing import Any
import httpx
from app.core.config import get_settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    finish_reason: str | None = None
    usage: dict | None = None
    raw_provider_name: str = "openai_compatible"


class LLMClient:
    def __init__(self):
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", **self.settings.llm_extra_headers}
        if self.settings.llm_auth_mode == "bearer":
            h["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        return h

    async def chat(self, messages: list[dict], tools: list[dict] | None = None, tool_choice: str = "auto") -> LLMResponse:
        if not self.settings.llm_configured:
            raise RuntimeError("LLM is not configured")
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {"model": self.settings.llm_model, "messages": messages, "stream": False}
        if tools and self.settings.llm_native_tool_calling:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        last_error = None
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                    r = await client.post(url, headers=self._headers(), json=payload)
                if r.status_code in (429,) or r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"upstream {r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                data = r.json()
                choice = data["choices"][0]
                msg = choice["message"]
                tcalls = []
                for tc in msg.get("tool_calls") or []:
                    args_raw = tc["function"].get("arguments") or "{}"
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    tcalls.append(ToolCall(tc.get("id", "toolcall"), tc["function"]["name"], args))
                return LLMResponse(
                    text=msg.get("content") or "", tool_calls=tcalls,
                    finish_reason=choice.get("finish_reason"), usage=data.get("usage")
                )
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
                last_error = e
                if attempt < self.settings.llm_max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"LLM request failed: {type(last_error).__name__}: {last_error}")
