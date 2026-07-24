"""Configuracao de logging estruturado do Worker.

Chama logging.basicConfig explicitamente - sem isso, o logger raiz do
Python usa o nivel padrao (WARNING) e descarta silenciosamente qualquer
logger.info(...). Esse exato bug ja foi encontrado e corrigido no backend
(ver SPRINT7_REPORT.md) e e evitado aqui desde o primeiro commit do Worker.

Deployment v1.0 (Docker): `settings.log_dir`, quando configurado (`WORKER_LOG_DIR`),
adiciona um `RotatingFileHandler` (log rotacionado, montavel como volume
`/app/logs`) - ADITIVO ao `StreamHandler` existente, nunca no lugar dele
(`docker logs` continua funcionando normalmente). Vazio (padrao) preserva
exatamente o comportamento de antes desta sprint - nenhum teste existente
foi afetado.
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from worker.config.settings import WorkerSettings

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

_MAX_LOG_FILE_BYTES = 10_000_000
_LOG_FILE_BACKUP_COUNT = 5


def configure_logging(settings: WorkerSettings) -> None:
    """Configura o logging raiz do processo a partir do nivel definido em settings.

    Usa force=True: sem isso, logging.basicConfig nao faz nada se o logger
    raiz ja tiver handlers configurados (por exemplo, por pytest ou por
    alguma dependencia importada antes) - o que tornaria a configuracao de
    nivel/formato nao deterministica dependendo da ordem de import.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if settings.log_dir:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_dir / "worker.log",
                maxBytes=_MAX_LOG_FILE_BYTES,
                backupCount=_LOG_FILE_BACKUP_COUNT,
            )
        )

    logging.basicConfig(level=level, format=LOG_FORMAT, handlers=handlers, force=True)
