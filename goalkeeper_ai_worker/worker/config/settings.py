"""Configuracao centralizada do Worker.

Nenhum valor sensivel e hardcoded: tudo e lido do arquivo .env (ou do
ambiente do processo). Nao compartilha nenhum campo, arquivo ou schema
com a configuracao do backend (Boundary Enforcement - ver
AI_WORKER_CONSTITUTION.md).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from worker.core.exceptions import ConfigurationError


class WorkerSettings(BaseSettings):
    """Configuracao de runtime de uma instancia do Worker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WORKER_",
        extra="ignore",
    )

    env: str = Field(
        default="development",
        description="Ambiente de execucao (development|production).",
    )
    instance_id: str = Field(
        description="Identificador unico desta instancia de Worker (Worker Instance).",
    )
    log_level: str = Field(
        default="INFO",
        description="Nivel de log (DEBUG|INFO|WARNING|ERROR).",
    )

    # --- Redis (fila de processamento - Sprint W2) ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL do Redis - deve ser o mesmo Redis usado pelo backend.",
    )
    consumer_group: str = Field(
        default="goalkeeper_ai_worker",
        description="Nome do consumer group do stream `processing_jobs`. "
        "Fixo por convencao entre instancias - todas devem usar o mesmo "
        "grupo para balancear carga corretamente.",
    )

    # --- Worker API do backend (Sprint W2) ---
    backend_api_url: str = Field(
        description="URL base da Worker API do backend (ex.: http://localhost:8001).",
    )
    api_key: str = Field(
        description="Segredo enviado no header X-Worker-Api-Key. Mesmo VALOR "
        "configurado como WORKER_API_KEY no backend - cada lado mantem seu "
        "proprio arquivo de configuracao (Boundary Enforcement).",
    )

    # --- Lock distribuido por video (Sprint W2, ADR-001/003) ---
    lock_ttl_seconds: int = Field(
        default=300,
        description="TTL do lock distribuido por video, em segundos.",
    )

    # --- Identificacao de protocolo (Sprint W2) ---
    protocol_version: str = Field(
        default="1.0",
        description="Versao do contrato REST falado com o backend (enviada "
        "no header X-Worker-Version). Distinta de worker.__version__, que e "
        "a versao do software do Worker.",
    )


@lru_cache
def get_settings() -> WorkerSettings:
    """Carrega (e armazena em cache) a configuracao do Worker a partir do .env."""
    try:
        return WorkerSettings()
    except Exception as exc:
        raise ConfigurationError(f"Configuracao invalida ou incompleta: {exc}") from exc
