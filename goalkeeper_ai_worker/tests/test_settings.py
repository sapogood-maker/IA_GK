"""Testes de worker.config.settings."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.core.exceptions import ConfigurationError


def test_settings_load_from_environment() -> None:
    """Os valores definidos via variaveis de ambiente devem ser carregados corretamente."""
    settings = get_settings()
    assert settings.instance_id == "worker-test-01"
    assert settings.env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.backend_api_url == "http://backend.test"
    assert settings.api_key == "test-api-key"


def test_settings_defaults_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    """Campos opcionais devem assumir seus valores padrao quando nao definidos."""
    monkeypatch.delenv("WORKER_ENV", raising=False)
    monkeypatch.delenv("WORKER_LOG_LEVEL", raising=False)
    monkeypatch.delenv("WORKER_REDIS_URL", raising=False)
    monkeypatch.delenv("WORKER_CONSUMER_GROUP", raising=False)
    monkeypatch.delenv("WORKER_LOCK_TTL_SECONDS", raising=False)
    monkeypatch.delenv("WORKER_PROTOCOL_VERSION", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.env == "development"
    assert settings.log_level == "INFO"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.consumer_group == "goalkeeper_ai_worker"
    assert settings.lock_ttl_seconds == 300
    assert settings.protocol_version == "1.0"


def test_missing_instance_id_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_INSTANCE_ID e obrigatorio - sua ausencia deve falhar de forma clara."""
    monkeypatch.delenv("WORKER_INSTANCE_ID", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()


def test_missing_backend_api_url_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_BACKEND_API_URL e obrigatorio - sua ausencia deve falhar de forma clara."""
    monkeypatch.delenv("WORKER_BACKEND_API_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()


def test_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_API_KEY e obrigatorio - sua ausencia deve falhar de forma clara."""
    monkeypatch.delenv("WORKER_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()
