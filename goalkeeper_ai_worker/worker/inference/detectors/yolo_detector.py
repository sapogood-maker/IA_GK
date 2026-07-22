"""YOLODetector: primeira implementação real de `Detector`, usando
Ultralytics YOLO.

Todo código Ultralytics (carregar modelo, rodar inferência, pós-
processar caixas) fica exclusivamente aqui - nenhum outro módulo do
Worker importa `ultralytics`."""
from __future__ import annotations

import time

import numpy as np
from ultralytics import YOLO

from worker.config.settings import WorkerSettings
from worker.inference.detectors.base import Detector
from worker.inference.detectors.exceptions import DetectorExecutionError, DetectorInitializationError
from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult


class YOLODetector(Detector):
    """Detector de objetos baseado num modelo YOLO (ex.: YOLO11n)."""

    name = "yolo"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._confidence_threshold = settings.confidence_threshold
        self._iou_threshold = settings.iou_threshold
        try:
            self._model = YOLO(settings.model_path)
        except Exception as exc:
            raise DetectorInitializationError(
                f"Falha ao carregar o modelo YOLO em '{settings.model_path}': {exc}"
            ) from exc

    def detect(self, frame: np.ndarray) -> DetectionResult:
        start = time.monotonic()
        try:
            results = self._model.predict(
                frame,
                conf=self._confidence_threshold,
                iou=self._iou_threshold,
                verbose=False,
            )
        except Exception as exc:
            raise DetectorExecutionError(f"Falha na inferencia YOLO: {exc}") from exc
        duration_ms = (time.monotonic() - start) * 1000

        detections: list[Detection] = []
        if results:
            result = results[0]
            boxes = result.boxes
            names = result.names
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    detections.append(
                        Detection(
                            label=ClassLabel(names.get(class_id, str(class_id))),
                            confidence=Confidence(confidence),
                            bbox=BoundingBox(
                                x=int(x1),
                                y=int(y1),
                                width=int(x2 - x1),
                                height=int(y2 - y1),
                            ),
                        )
                    )

        return DetectionResult(
            detections=detections,
            model_name=self.name,
            model_version=self.version,
            duration_ms=duration_ms,
        )
