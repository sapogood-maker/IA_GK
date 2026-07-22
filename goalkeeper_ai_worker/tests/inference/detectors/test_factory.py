"""Testes de worker.inference.detectors.factory.create_detector."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.detectors.base import Detector
from worker.inference.detectors.exceptions import DetectorInitializationError
from worker.inference.detectors.factory import create_detector
from worker.inference.detectors.registry import register_detector
from worker.inference.detectors.types import DetectionResult


def test_create_detector_raises_for_unknown_name() -> None:
    settings = get_settings()
    with pytest.raises(DetectorInitializationError):
        create_detector("nao-existe", settings)


class _FailingDetector(Detector):
    """Detector cuja inicializacao sempre falha - prova que factory.py
    envolve qualquer excecao de __init__ numa DetectorInitializationError,
    nunca deixando vazar a excecao original sem contexto."""

    name = "failing"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        raise RuntimeError("pesos nao encontrados")

    def detect(self, frame: np.ndarray) -> DetectionResult:
        raise AssertionError("nunca deveria ser chamado")


def test_create_detector_wraps_initialization_failures() -> None:
    register_detector("failing-test-detector", _FailingDetector)
    settings = get_settings()

    with pytest.raises(DetectorInitializationError):
        create_detector("failing-test-detector", settings)
