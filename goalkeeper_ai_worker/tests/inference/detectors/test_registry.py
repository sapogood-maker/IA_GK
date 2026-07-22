"""Testes de worker.inference.detectors.registry."""
from __future__ import annotations

import numpy as np

from worker.inference.detectors.base import Detector
from worker.inference.detectors.registry import (
    available_detectors,
    get_detector_class,
    register_detector,
)
from worker.inference.detectors.types import DetectionResult
from worker.inference.detectors.yolo_detector import YOLODetector


def test_yolo_detector_is_registered() -> None:
    assert "yolo" in available_detectors()
    assert get_detector_class("yolo") is YOLODetector


def test_get_detector_class_returns_none_for_unknown_name() -> None:
    assert get_detector_class("nao-existe") is None


class _DummyDetector(Detector):
    """Detector de teste - prova que registrar um Detector novo e
    suficiente para disponibiliza-lo via configuracao, sem alterar
    YOLOProcessor nem factory.py."""

    name = "dummy"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        pass

    def detect(self, frame: np.ndarray) -> DetectionResult:
        return DetectionResult(model_name=self.name, model_version=self.version)


def test_registering_a_new_detector_makes_it_available() -> None:
    register_detector("dummy-test-detector", _DummyDetector)

    assert "dummy-test-detector" in available_detectors()
    assert get_detector_class("dummy-test-detector") is _DummyDetector
