from __future__ import annotations

import json
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/app.db"

    llm_provider: str = "openai_compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    llm_auth_mode: str = "bearer"
    llm_extra_headers_json: str = "{}"
    llm_native_tool_calling: bool = True
    llm_streaming: bool = False

    monitor_interval_minutes: int = 60
    price_change_trigger_percent: float = 5.0
    agent_max_steps: int = 6
    default_max_price_change_percent: float = 10.0
    demo_fallback_enabled: bool = True

    # 淘宝只做手动查询。首次登录由 backend/scripts/taobao_login.py 完成，
    # 查询接口只复用这里的 Playwright storage state，不保存账号密码。
    taobao_storage_state_path: str = "./data/taobao_profile/storage_state.json"
    # Render/云端部署可把 storage_state.json 转成 Base64 后写入该环境变量。
    # 若配置，则查询时会优先用它初始化登录状态文件；变量本身不会写入日志。
    taobao_storage_state_b64: str = ""
    taobao_search_timeout_seconds: int = 35
    taobao_headless: bool = True
    taobao_max_scan_items: int = 60

    @property
    def llm_extra_headers(self) -> dict[str, str]:
        try:
            value = json.loads(self.llm_extra_headers_json or "{}")
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model and self.llm_api_key != "replace_me")


@lru_cache
def get_settings() -> Settings:
    return Settings()
