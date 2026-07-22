"""Testes de worker.inference.detectors.types - tipos proprios da API de
Deteccao, nunca listas de dicionarios soltos."""
from __future__ import annotations

from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult


def test_detection_result_to_dict_serializes_bbox_and_detections() -> None:
    detection = Detection(
        label=ClassLabel("goalkeeper"),
        confidence=Confidence(0.87),
        bbox=BoundingBox(x=10, y=20, width=30, height=40),
    )
    result = DetectionResult(
        detections=[detection], frame_index=5, model_name="yolo", model_version="1.0.0", duration_ms=12.5
    )

    payload = result.to_dict()

    assert payload["frame_index"] == 5
    assert payload["model_name"] == "yolo"
    assert payload["model_version"] == "1.0.0"
    assert payload["duration_ms"] == 12.5
    assert payload["detections"] == [
        {
            "label": "goalkeeper",
            "confidence": 0.87,
            "bbox": {"x": 10, "y": 20, "width": 30, "height": 40},
        }
    ]


def test_detection_result_defaults_to_no_detections() -> None:
    result = DetectionResult()

    assert result.detections == []
    assert result.to_dict()["detections"] == []
