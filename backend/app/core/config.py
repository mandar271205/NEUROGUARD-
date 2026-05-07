from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def default_model_dir() -> str:
    for folder_name in ("PDS MODEL 2", "PDS MODEL1"):
        local_colab_dir = PROJECT_ROOT / folder_name
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
    polygon_amoy_rpc_url: str | None = Field(default=None, alias="POLYGON_AMOY_RPC_URL")
    consent_contract_address: str | None = Field(default=None, alias="CONSENT_CONTRACT_ADDRESS")
    audit_contract_address: str | None = Field(default=None, alias="AUDIT_CONTRACT_ADDRESS")
    external_stress_repo_dir: str = Field(
        default=str(PROJECT_ROOT / "third_party" / "Stress-Detection-Through-Speech-Emotion-Recognition"),
        alias="EXTERNAL_STRESS_REPO_DIR",
    )
    audio_student_checkpoint: str = Field(
        default=str(BACKEND_ROOT / "models" / "neuroguard_audio_student.pt"),
        alias="AUDIO_STUDENT_CHECKPOINT",
    )
    stress_baseline_weight: float = Field(default=0.2, alias="STRESS_BASELINE_WEIGHT")
    aamo_window_size: int = Field(default=50, alias="AAMO_WINDOW_SIZE")
    aamo_min_window_for_adaptive: int = Field(default=10, alias="AAMO_MIN_WINDOW_FOR_ADAPTIVE")
    aamo_cold_start_weight_baseline: float = Field(default=0.7, alias="AAMO_COLD_START_WEIGHT_BASELINE")
    aamo_cold_start_weight_neuroguard: float = Field(default=0.3, alias="AAMO_COLD_START_WEIGHT_NEUROGUARD")
    aamo_critical_health_threshold: float = Field(default=0.2, alias="AAMO_CRITICAL_HEALTH_THRESHOLD")
    aamo_fallback_weight_baseline: float = Field(default=0.95, alias="AAMO_FALLBACK_WEIGHT_BASELINE")
    aamo_fallback_weight_neuroguard: float = Field(default=0.05, alias="AAMO_FALLBACK_WEIGHT_NEUROGUARD")
    aamo_neuroguard_boost_factor: float = Field(default=1.5, alias="AAMO_NEUROGUARD_BOOST_FACTOR")
    aamo_health_variance_weight: float = Field(default=0.5, alias="AAMO_HEALTH_VARIANCE_WEIGHT")
    aamo_health_range_weight: float = Field(default=0.3, alias="AAMO_HEALTH_RANGE_WEIGHT")
    aamo_health_mode_penalty_weight: float = Field(default=0.2, alias="AAMO_HEALTH_MODE_PENALTY_WEIGHT")
    aamo_expected_var_baseline: float = Field(default=0.05, alias="AAMO_EXPECTED_VAR_BASELINE")
    aamo_expected_var_neuroguard: float = Field(default=0.05, alias="AAMO_EXPECTED_VAR_NEUROGUARD")
    aamo_expected_range: float = Field(default=0.6, alias="AAMO_EXPECTED_RANGE")

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
