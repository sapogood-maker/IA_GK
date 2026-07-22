"""Testes de worker.inference.trackers.factory.create_tracker."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.inference.detectors.types import DetectionResult
from worker.inference.trackers.base import Tracker
from worker.inference.trackers.exceptions import TrackerInitializationError
from worker.inference.trackers.factory import create_tracker
from worker.inference.trackers.registry import register_tracker
from worker.inference.trackers.types import TrackingResult


def test_create_tracker_raises_for_unknown_name() -> None:
    settings = get_settings()
    with pytest.raises(TrackerInitializationError):
        create_tracker("nao-existe", settings)


class _FailingTracker(Tracker):
    """Tracker cuja inicializacao sempre falha - prova que factory.py
    envolve qualquer excecao de __init__ numa TrackerInitializationError."""

    name = "failing"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        raise RuntimeError("falha de inicializacao")

    def track(self, detections: DetectionResult) -> TrackingResult:
        raise AssertionError("nunca deveria ser chamado")


def test_create_tracker_wraps_initialization_failures() -> None:
    register_tracker("failing-test-tracker", _FailingTracker)
    settings = get_settings()

    with pytest.raises(TrackerInitializationError):
        create_tracker("failing-test-tracker", settings)


def test_create_tracker_resolves_bytetrack() -> None:
    settings = get_settings()
    tracker = create_tracker("bytetrack", settings)
    assert tracker.name == "bytetrack"
