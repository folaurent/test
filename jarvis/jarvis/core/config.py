"""Config centrale Jarvis. Source unique de vérité pour tout le runtime.

Tout lit les settings via `get_settings()` (cached). Ne jamais lire os.environ
directement ailleurs — ça casse l'audit trail et les tests.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environnement
    env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    dry_run: bool = True

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_allowed_user_ids: str = ""
    telegram_allowed_chat_ids: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_key: SecretStr = SecretStr("")
    supabase_anon_key: SecretStr = SecretStr("")

    # LLM
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_zdr: bool = False
    openai_api_key: SecretStr = SecretStr("")
    ollama_host: str = "http://ollama:11434"
    ollama_fallback_model: str = "llama3.3"

    # Model routing (tier → model id)
    model_router_tier: str = "claude-haiku-4-5-20251001"
    model_standard_tier: str = "claude-sonnet-4-6"
    model_critical_tier: str = "claude-opus-4-7"

    # Budgets
    budget_llm_eur_month: float = 200.0
    budget_infra_eur_month: float = 100.0
    budget_tokens_month: int = 50_000_000
    budget_user_questions_per_day: int = 30
    budget_hard_stop: bool = True

    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080
    dashboard_auth_token: SecretStr = SecretStr("")

    # Security
    kill_switch_token: SecretStr = SecretStr("")
    secrets_master_key: SecretStr = SecretStr("")
    canary_secret: SecretStr = SecretStr("")

    # Backup
    s3_backup_bucket: str = ""
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    s3_endpoint: str = ""

    # Scope (NE PAS MODIFIER — double verrou en dur dans le code)
    scope_excluded_ventures: str = "sika,parexlanko"

    # Git
    git_signing_key: str = ""

    @field_validator("scope_excluded_ventures")
    @classmethod
    def _scope_always_includes_sika_parexlanko(cls, v: str) -> str:
        lowered = {t.strip().lower() for t in v.split(",") if t.strip()}
        required = {"sika", "parexlanko"}
        if not required.issubset(lowered):
            # Verrou dur : ne jamais retirer sika/parexlanko, même par env var.
            lowered |= required
        return ",".join(sorted(lowered))

    @property
    def excluded_ventures(self) -> frozenset[str]:
        return frozenset(
            t.strip().lower()
            for t in self.scope_excluded_ventures.split(",")
            if t.strip()
        )

    @property
    def allowed_telegram_user_ids(self) -> frozenset[int]:
        return frozenset(
            int(x) for x in self.telegram_allowed_user_ids.split(",") if x.strip()
        )

    @property
    def allowed_telegram_chat_ids(self) -> frozenset[int]:
        return frozenset(
            int(x) for x in self.telegram_allowed_chat_ids.split(",") if x.strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Utilisé par les tests uniquement."""
    get_settings.cache_clear()
