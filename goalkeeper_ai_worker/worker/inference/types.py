"""Tipos proprios da camada de inferencia - nunca dicionarios soltos.

`Detection` continua minima (sem IA real ainda). `FrameMetadata`, desde a
Sprint W5, ja recebe valores reais (via worker.video) - o contrato
consumido pelo restante do Pipeline nao mudou, so deixou de ser sempre
zerado. `RegionOfInterest` e os campos `frames_processed`/`frame_skip`/
`roi` de `InferenceResult` foram adicionados na Sprint W6 para o
`BasicVisionEngine`, sem quebrar `FakeInferenceEngine` (todos opcionais,
default `None`).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Detection:
    """Um objeto detectado num frame - minimo por enquanto."""

    label: str
    confidence: float
    frame_index: int = 0


@dataclass(frozen=True)
class FrameMetadata:
    """Metadados do video processado (contagem de frames, dimensoes, fps,
    duracao).

    Desde a Sprint W5, populado com valores REAIS a partir de
    worker.video.types.VideoProperties (lido pelo VideoReader) - antes
    (W4) ficava sempre zerado, pois nenhum motor decodificava video de
    verdade. Desde a W6, `width`/`height` podem refletir a resolucao APOS
    resize/ROI (nao mais so a resolucao original do video), a depender do
    motor."""

    frame_count: int = 0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class RegionOfInterest:
    """Uma regiao retangular de interesse dentro do frame (Sprint W6)."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class InferenceMetadata:
    """Metadados sobre a propria execucao de inferencia (qual motor, versao,
    duracao) - base do que futuramente vira Model Versions/Pipeline Version
    (AI_WORKER_CONSTITUTION.md, Secao 8)."""

    engine_name: str
    engine_version: str
    duration_ms: float


@dataclass
class InferenceResult:
    """Resultado completo de uma execucao de inferencia - o que vira o
    artefato JSON gerado pelo motor.

    `frames_processed`/`frame_skip`/`roi` (Sprint W6) sao opcionais -
    `FakeInferenceEngine` nunca os preenche (ficam `None`); `BasicVisionEngine`
    os preenche sempre."""

    status: str
    detections: list[Detection] = field(default_factory=list)
    frame_metadata: FrameMetadata = field(default_factory=FrameMetadata)
    metadata: InferenceMetadata | None = None
    frames_processed: int | None = None
    frame_skip: int | None = None
    roi: RegionOfInterest | None = None

    def to_dict(self) -> dict:
        """Serializa para o artefato JSON enviado ao R2."""
        return {
            "status": self.status,
            "detections": [
                {"label": d.label, "confidence": d.confidence, "frame_index": d.frame_index}
                for d in self.detections
            ],
            "frame_metadata": {
                "frame_count": self.frame_metadata.frame_count,
                "width": self.frame_metadata.width,
                "height": self.frame_metadata.height,
                "fps": self.frame_metadata.fps,
                "duration_seconds": self.frame_metadata.duration_seconds,
            },
            "metadata": (
                {
                    "engine_name": self.metadata.engine_name,
                    "engine_version": self.metadata.engine_version,
                    "duration_ms": self.metadata.duration_ms,
                }
                if self.metadata is not None
                else None
            ),
            "frames_processed": self.frames_processed,
            "frame_skip": self.frame_skip,
            "roi": (
                {"x": self.roi.x, "y": self.roi.y, "width": self.roi.width, "height": self.roi.height}
                if self.roi is not None
                else None
            ),
        }
