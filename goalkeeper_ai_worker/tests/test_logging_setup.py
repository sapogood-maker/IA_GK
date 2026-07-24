"""Testes de worker.observability.logging_setup."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import pytest

from worker.config.settings import get_settings
from worker.observability.logging_setup import configure_logging


def test_configure_logging_sets_root_level() -> None:
    """O nivel do logger raiz deve refletir WORKER_LOG_LEVEL."""
    settings = get_settings()
    configure_logging(settings)
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_emits_info_messages(capsys: pytest.CaptureFixture[str]) -> None:
    """Sem logging.basicConfig(force=True), logger.info(...) poderia ser descartado
    silenciosamente (mesma classe de bug corrigida no backend) ou capturado apenas
    pelo handler interno do pytest. Usa capsys (nao caplog) porque configure_logging
    usa force=True, que substitui deliberadamente qualquer handler pre-existente no
    logger raiz - inclusive o handler de captura do proprio pytest."""
    settings = get_settings()
    configure_logging(settings)
    logger = logging.getLogger("worker.test")

    logger.info("mensagem_de_teste")

    assert "mensagem_de_teste" in capsys.readouterr().err


def test_configure_logging_without_log_dir_adds_no_file_handler() -> None:
    """WORKER_LOG_DIR vazio (padrao) - mesmo comportamento de antes desta
    sprint, so o StreamHandler, nenhum RotatingFileHandler."""
    settings = get_settings()
    assert settings.log_dir == ""

    configure_logging(settings)

    root_handlers = logging.getLogger().handlers
    assert len(root_handlers) == 1
    assert isinstance(root_handlers[0], logging.StreamHandler)


def test_configure_logging_with_log_dir_writes_a_rotated_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deployment v1.0: WORKER_LOG_DIR configurado adiciona um
    RotatingFileHandler ADITIVO - o StreamHandler (docker logs) continua
    existindo."""
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("WORKER_LOG_DIR", str(log_dir))
    get_settings.cache_clear()
    settings = get_settings()

    configure_logging(settings)
    logger = logging.getLogger("worker.test_log_dir")
    logger.info("mensagem_persistida_em_arquivo")

    log_file = log_dir / "worker.log"
    assert log_file.exists()
    assert "mensagem_persistida_em_arquivo" in log_file.read_text(encoding="utf-8")

    root_handlers = logging.getLogger().handlers
    assert any(isinstance(h, logging.StreamHandler) for h in root_handlers)
    assert any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_handlers)
