"""Configuracao de logging estruturado do Worker.

Chama logging.basicConfig explicitamente - sem isso, o logger raiz do
Python usa o nivel padrao (WARNING) e descarta silenciosamente qualquer
logger.info(...). Esse exato bug ja foi encontrado e corrigido no backend
(ver SPRINT7_REPORT.md) e e evitado aqui desde o primeiro commit do Worker.
"""
from __future__ import annotations

import logging

from worker.config.settings import WorkerSettings

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(settings: WorkerSettings) -> None:
    """Configura o logging raiz do processo a partir do nivel definido em settings.

    Usa force=True: sem isso, logging.basicConfig nao faz nada se o logger
    raiz ja tiver handlers configurados (por exemplo, por pytest ou por
    alguma dependencia importada antes) - o que tornaria a configuracao de
    nivel/formato nao deterministica dependendo da ordem de import.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
