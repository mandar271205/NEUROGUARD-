from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def default_model_dir() -> str:
    local_colab_dir = PROJECT_ROOT / "PDS MODEL1"
    if local_colab_dir.exists():
        return str(local_colab_dir)
    return str(BACKEND_ROOT / "models")


class Settings(BaseSettings):
    app_name: str = "NeuroGuard API"
    api_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="API_CORS_ORIGINS",
    )
    model_dir: str = Field(default_factory=default_model_dir, alias="MODEL_DIR")

    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: str | None = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    supabase_jwt_audience: str | None = Field(
        default="authenticated", alias="SUPABASE_JWT_AUDIENCE"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def resolved_model_dir(self) -> Path:
        return Path(self.model_dir).expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
