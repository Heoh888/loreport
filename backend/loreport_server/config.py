from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    repo_path: str = "/repo"
    loreport_dir: str = "loreport"
    port: int = 3080
    loreport_data_dir: str = "/data"
    database_url: str | None = None
    webhook_secret: str | None = None
    loreport_provider: str = "openai"
    loreport_model_id: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    loreport_language: str = "en"
    static_dir: str | None = None

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        data_dir = Path(self.loreport_data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        db_file = data_dir / "loreport.db"
        return f"sqlite+aiosqlite:///{db_file}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
