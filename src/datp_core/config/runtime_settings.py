"""Environment and runtime settings configuration using Pydantic Settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("data")
    outputs_dir: Path = Path("outputs")
    cache_dir: Path = Path(".cache")
    max_workers: int = 4
    log_level: str = "INFO"
