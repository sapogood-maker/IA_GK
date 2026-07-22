"""Testes de worker.inference.trackers.registry."""
from __future__ import annotations

from worker.inference.detectors.types import DetectionResult
from worker.inference.trackers.base import Tracker
from worker.inference.trackers.bytetrack_tracker import ByteTrackTracker
from worker.inference.trackers.registry import (
    available_trackers,
    get_tracker_class,
    register_tracker,
)
from worker.inference.trackers.types import TrackingResult


def test_bytetrack_tracker_is_registered() -> None:
    assert "bytetrack" in available_trackers()
    assert get_tracker_class("bytetrack") is ByteTrackTracker


def test_get_tracker_class_returns_none_for_unknown_name() -> None:
    assert get_tracker_class("nao-existe") is None


class _DummyTracker(Tracker):
    """Tracker de teste - prova que registrar um Tracker novo e suficiente
    para disponibiliza-lo via configuracao, sem alterar TrackingProcessor
    nem factory.py."""

    name = "dummy"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        pass

    def track(self, detections: DetectionResult) -> TrackingResult:
        return TrackingResult(tracker_name=self.name, tracker_version=self.version)


def test_registering_a_new_tracker_makes_it_available() -> None:
    register_tracker("dummy-test-tracker", _DummyTracker)

    assert "dummy-test-tracker" in available_trackers()
    assert get_tracker_class("dummy-test-tracker") is _DummyTracker
