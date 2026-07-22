"""WorkspaceManager: cria e limpa o diretorio de trabalho temporario de um Job.

Sempre via `tempfile` - nunca um caminho hardcoded - garantindo isolamento
entre Jobs mesmo rodando na mesma maquina (Sprint W3).
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Gerencia o ciclo de vida do diretorio de trabalho temporario de um Job."""

    def create(self, job_id: str) -> Path:
        """Cria um diretorio temporario exclusivo para este Job."""
        workspace_dir = Path(tempfile.mkdtemp(prefix=f"goalkeeper_worker_{job_id}_"))
        logger.debug("workspace_created job_id=%s path=%s", job_id, workspace_dir)
        return workspace_dir

    def cleanup(self, workspace_dir: Path) -> None:
        """Remove o diretorio de trabalho e todo o seu conteudo."""
        shutil.rmtree(workspace_dir, ignore_errors=True)
        logger.debug("workspace_cleaned path=%s", workspace_dir)
