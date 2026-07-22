"""Interface única de todo Detector de objetos - Detector.

Contrato mínimo: `detect(frame) -> DetectionResult`. Nenhum Processor
conhece o framework por trás de um Detector concreto (Ultralytics,
Transformers, ou outro) - só este contrato. Trocar YOLO por RT-DETR/
GroundingDINO/OWLv2 nunca exige alterar `YOLOProcessor` nem qualquer
outro Processor - só escrever uma nova classe que implemente esta
interface e registrá-la (`registry.py`)."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.detectors.types import DetectionResult


class Detector(ABC):
    """Uma única responsabilidade: detectar objetos num frame já
    pré-processado pela pipeline de Processors."""

    name: str
    version: str

    def __init__(self, settings: WorkerSettings) -> None:
        """Todo Detector registrado é construído com `settings` (mesma
        convenção uniforme já usada por InferenceEngine/FrameProcessor)."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Executa a detecção sobre um único frame, devolvendo um
        DetectionResult - nunca uma lista de dicionários solta."""
        ...
