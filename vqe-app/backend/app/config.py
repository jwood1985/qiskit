"""Application configuration."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Static, environment-derived configuration.

    Per-provider tokens are NOT stored here — they live in the encrypted
    secrets store so they survive process restarts without leaking into
    environment dumps.
    """

    model_config = SettingsConfigDict(env_prefix="VQE_APP_", env_file=".env", extra="ignore")

    # Filesystem location of the Fernet-encrypted token store.
    data_dir: Path = Path(os.path.expanduser("~/.vqe-app"))

    # Optional master secret used to derive the Fernet key. If unset, a key
    # is generated on first run and persisted next to the ciphertext.
    secret: str | None = None

    # Dynatrace OTLP target. The Dynatrace API token itself is stored in the
    # secrets store under the "dynatrace" provider entry.
    otlp_endpoint: str = "https://qof78400.live.dynatrace.com/api/v2/otlp"
    service_name: str = "vqe-app-backend"

    # CORS origin for the Vite dev server.
    frontend_origin: str = "http://localhost:5173"


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
        _config.data_dir.mkdir(parents=True, exist_ok=True)
    return _config
