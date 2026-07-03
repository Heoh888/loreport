from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LoreportMode = Literal["standalone", "distributed"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    repo_path: str = "/repo"
    loreport_dir: str = "loreport"
    port: int = 3080
    loreport_mode: LoreportMode = "standalone"
    loreport_data_dir: str = "/data"
    database_url: str | None = None
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    poll_interval_sec: int = 300
    webhook_secret: str | None = None
    loreport_provider: str = "openai"
    loreport_model_id: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    loreport_language: str = "en"
    static_dir: str | None = None

    sync_exchange: str = "loreport.sync"
    sync_queue: str = "loreport.sync.jobs"
    sync_routing_key: str = "sync"

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.loreport_mode == "standalone":
            data_dir = Path(self.loreport_data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            db_file = data_dir / "loreport.db"
            return f"sqlite+aiosqlite:///{db_file}"
        return "postgresql+asyncpg://loreport:loreport@postgres/loreport"

    @property
    def is_standalone(self) -> bool:
        return self.loreport_mode == "standalone"


@lru_cache
def get_settings() -> Settings:
    return Settings()
