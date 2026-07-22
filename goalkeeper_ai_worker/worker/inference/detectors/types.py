"""Tipos próprios da API de Detecção - nunca listas de dicionários soltos.

Distintos dos tipos de `worker.inference.types` (que descrevem o artefato
final do motor de inferência): estes descrevem especificamente a saída de
um `Detector` - uma unidade menor, reutilizável por qualquer Processor
que precise detectar objetos (não só `YOLOProcessor`)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NewType

# Tipos leves (NewType - identidade em runtime, sem overhead de wrapper),
# só para nomear o dominio em vez de usar `str`/`float` cru nas assinaturas.
ClassLabel = NewType("ClassLabel", str)
Confidence = NewType("Confidence", float)


@dataclass(frozen=True)
class BoundingBox:
    """Caixa delimitadora de uma detecção, em pixels, relativa ao frame
    (já pós-Processors anteriores da pipeline - ex.: pós-resize/ROI)."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Detection:
    """Um objeto detectado num frame por um `Detector`."""

    label: ClassLabel
    confidence: Confidence
    bbox: BoundingBox


@dataclass
class DetectionResult:
    """Resultado completo de uma chamada a `Detector.detect(frame)`."""

    detections: list[Detection] = field(default_factory=list)
    frame_index: int = 0
    model_name: str = ""
    model_version: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "duration_ms": self.duration_ms,
            "detections": [
                {
                    "label": detection.label,
                    "confidence": detection.confidence,
                    "bbox": {
                        "x": detection.bbox.x,
                        "y": detection.bbox.y,
                        "width": detection.bbox.width,
                        "height": detection.bbox.height,
                    },
                }
                for detection in self.detections
            ],
        }
