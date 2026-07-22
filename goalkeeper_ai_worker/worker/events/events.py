"""Eventos internos do ciclo de vida de um Job - por enquanto apenas logging.

Nota de nomenclatura: `AI_WORKER_CONSTITUTION.md` reservava `events/`
originalmente para o Event Registry (Plugins de evento tecnico - Defesa,
Saida, etc., Sprint W5). Esta sprint (W3) reaproveita a mesma pasta para
eventos internos operacionais (ciclo de vida do Job), por instrucao
explicita do usuario. Os dois conceitos podem conviver aqui, mas vale
reavaliar - antes da W5 - se merecem modulos/nomes separados para evitar
confusao entre "evento tecnico detectado no video" e "evento de ciclo de
vida do Worker".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobStarted:
    """O Worker comecou a processar este Job."""

    job_id: str
    video_id: str


@dataclass(frozen=True)
class VideoDownloaded:
    """O video original foi baixado para o workspace local."""

    job_id: str
    video_id: str
    download_path: str


@dataclass(frozen=True)
class ArtifactGenerated:
    """Um artefato foi gerado no workspace local."""

    job_id: str
    video_id: str
    artifact_path: str


@dataclass(frozen=True)
class UploadFinished:
    """O artefato foi enviado ao R2 com sucesso."""

    job_id: str
    video_id: str
    r2_key: str


@dataclass(frozen=True)
class JobCompleted:
    """O Job foi concluido com sucesso, de ponta a ponta."""

    job_id: str
    video_id: str


@dataclass(frozen=True)
class JobFailed:
    """O Job falhou em algum Stage do Pipeline."""

    job_id: str
    video_id: str
    error: str


def emit(event: object) -> None:
    """Loga o evento - unico "consumidor" nesta sprint. video_id/job_id
    (Correlation ID - AI_WORKER_CONSTITUTION.md, Secao 3) sempre presentes,
    pois fazem parte de todo dataclass de evento. Preparado para, no
    futuro, tambem alimentar metricas (Secao 11), sem mudar quem chama
    `emit`."""
    logger.info("%s %s", type(event).__name__, event)
