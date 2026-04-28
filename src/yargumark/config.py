from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mode: str = Field(default="demo", alias="MODE")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-haiku-20241022",
        alias="ANTHROPIC_MODEL",
    )
    db_path: Path = Field(default=Path("data/yargumark.db"), alias="DB_PATH")
    demo_confidence_threshold: float = Field(default=0.9, alias="DEMO_CONFIDENCE_THRESHOLD")
    production_confidence_threshold: float = Field(
        default=0.5,
        alias="PRODUCTION_CONFIDENCE_THRESHOLD",
    )
    context_check_low: float = Field(default=0.6, alias="CONTEXT_CHECK_LOW")
    context_check_high: float = Field(default=0.9, alias="CONTEXT_CHECK_HIGH")
    fuzzy_min_score: int = Field(default=88, alias="FUZZY_MIN_SCORE")


def get_settings() -> Settings:
    return Settings()


def ui_threshold(settings: Settings, ui_mode: str | None) -> float:
    mode = (ui_mode or settings.mode or "demo").strip().lower()
    if mode == "production":
        return float(settings.production_confidence_threshold)
    return float(settings.demo_confidence_threshold)
