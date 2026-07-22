"""Testes de YOLODetector - usa o modelo real (YOLO11n, pequeno, baixado
uma vez pela Ultralytics e cacheado) contra frames sinteticos. Mockar
apenas a inferencia em si (Processor/pipeline) faz sentido para testes de
integracao mais amplos - aqui, testar o Detector de verdade e o unico
jeito de provar que a conversao de saida do Ultralytics para
DetectionResult realmente funciona."""
from __future__ import annotations

import numpy as np

from worker.config.settings import get_settings
from worker.inference.detectors.types import BoundingBox, DetectionResult
from worker.inference.detectors.yolo_detector import YOLODetector


def test_detect_returns_a_well_formed_detection_result() -> None:
    settings = get_settings()
    detector = YOLODetector(settings)
    frame = np.random.randint(0, 256, size=(480, 640, 3), dtype=np.uint8)

    result = detector.detect(frame)

    assert isinstance(result, DetectionResult)
    assert result.model_name == "yolo"
    assert result.model_version == detector.version
    assert result.duration_ms >= 0.0
    for detection in result.detections:
        assert isinstance(detection.label, str)  # ClassLabel e um NewType de str
        assert isinstance(detection.confidence, float)  # Confidence e um NewType de float
        assert 0.0 <= detection.confidence <= 1.0
        assert isinstance(detection.bbox, BoundingBox)
        assert detection.bbox.width >= 0
        assert detection.bbox.height >= 0


def test_detect_respects_confidence_threshold_configuration() -> None:
    settings = get_settings()
    detector = YOLODetector(settings)
    assert detector._confidence_threshold == settings.confidence_threshold
    assert detector._iou_threshold == settings.iou_threshold
