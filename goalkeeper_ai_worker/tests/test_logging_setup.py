"""Testes de worker.observability.logging_setup."""
from __future__ import annotations

import logging

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
