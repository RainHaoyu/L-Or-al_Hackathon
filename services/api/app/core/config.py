"""全局配置：模型号全部配置化（后台升级不改代码）。

环境变量见 .env.example：
    DASHSCOPE_API_KEY   百炼 API Key（缺省时自动进入 mock 模式，识别/文案走本地模拟）
    QWEN_VISION_MODEL   默认 qwen-vl-max
    QWEN_TEXT_MODEL     默认 qwen-max（降级备选 qwen-plus）
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]  # 仓库根：services/api/app/core -> <root>
DATA_DIR = REPO_ROOT / "data" / "seed"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "unbounded-api"
    engine_version: str = "qra2@1.0.0"

    # —— 阿里云百炼（DashScope）OpenAI 兼容模式 ——
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_vision_model: str = "qwen-vl-max"
    qwen_text_model: str = "qwen-max"
    qwen_text_model_fallback: str = "qwen-plus"

    # —— 读光 OCR / 视觉智能条码识别（阿里云，凭证待接入，当前 stub+mock） ——
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""

    data_dir: Path = DATA_DIR
    cors_origins: str = "*"

    @property
    def mock_mode(self) -> bool:
        """未配置 DashScope Key 时自动降级为本地 mock（演示兜底，不阻断开发）。"""
        return not self.dashscope_api_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
