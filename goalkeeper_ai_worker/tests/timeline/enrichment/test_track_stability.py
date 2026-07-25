"""Testes de worker.timeline.enrichment.enrichers.track_stability.
TrackStabilityEnricher."""
from __future__ import annotations

from worker.timeline.enrichment.enrichers.track_stability import TrackStabilityEnricher
from worker.timeline.enrichment.event_types import TRACK_STABLE, TRACK_UNSTABLE


def _event(event_id: str, event_type: str, frame_index: int, track_id: int, timestamp_seconds: float) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds,
        "track_id": track_id,
        "entity": "person",
        "confidence": None,
        "position": None,
        "metadata": {},
        "parent_event_id": None,
    }


def test_no_events_produces_no_derived_events():
    assert TrackStabilityEnricher().enrich([]) == []


def test_disruptions_within_window_emit_unstable_once():
    events = [
        _event("e1", "TrackLost", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "OcclusionDetected", 10, track_id=1, timestamp_seconds=1.0),
        _event("e3", "TrackLost", 20, track_id=1, timestamp_seconds=2.0),
    ]
    derived = TrackStabilityEnricher(unstable_threshold_count=2, window_seconds=5.0).enrich(events)
    unstable_events = [e for e in derived if e.event_type == TRACK_UNSTABLE]
    assert len(unstable_events) == 1  # so no 2o evento, que cruzou o limiar - nao repete no 3o
    assert unstable_events[0].parent_event_id == "e2"


def test_disruptions_outside_window_do_not_trigger_unstable():
    events = [
        _event("e1", "TrackLost", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "TrackLost", 100, track_id=1, timestamp_seconds=10.0),  # fora da janela de 5s
    ]
    derived = TrackStabilityEnricher(unstable_threshold_count=2, window_seconds=5.0).enrich(events)
    assert [e for e in derived if e.event_type == TRACK_UNSTABLE] == []


def test_track_stable_after_clean_period_since_first_seen():
    events = [
        _event("e1", "TrackUpdated", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "TrackUpdated", 60, track_id=1, timestamp_seconds=6.0),
    ]
    derived = TrackStabilityEnricher(stable_duration_seconds=5.0).enrich(events)
    stable_events = [e for e in derived if e.event_type == TRACK_STABLE]
    assert len(stable_events) == 1
    assert stable_events[0].parent_event_id == "e2"
    assert stable_events[0].metadata["stable_seconds"] == 6.0


def test_track_stable_measured_since_last_disruption_not_since_first_seen():
    events = [
        _event("e1", "TrackUpdated", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "TrackLost", 10, track_id=1, timestamp_seconds=1.0),
        _event("e3", "TrackUpdated", 70, track_id=1, timestamp_seconds=7.0),
    ]
    derived = TrackStabilityEnricher(stable_duration_seconds=5.0, unstable_threshold_count=99).enrich(events)
    stable_events = [e for e in derived if e.event_type == TRACK_STABLE]
    assert len(stable_events) == 1
    # 7.0 - 1.0 (ultima disrupcao) = 6.0, nao 7.0 - 0.0
    assert stable_events[0].metadata["stable_seconds"] == 6.0


def test_stable_not_emitted_before_threshold():
    events = [
        _event("e1", "TrackUpdated", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "TrackUpdated", 10, track_id=1, timestamp_seconds=1.0),
    ]
    derived = TrackStabilityEnricher(stable_duration_seconds=5.0).enrich(events)
    assert [e for e in derived if e.event_type == TRACK_STABLE] == []


def test_stable_only_emitted_once_per_clean_streak():
    events = [
        _event("e1", "TrackUpdated", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "TrackUpdated", 60, track_id=1, timestamp_seconds=6.0),
        _event("e3", "TrackUpdated", 120, track_id=1, timestamp_seconds=12.0),
    ]
    derived = TrackStabilityEnricher(stable_duration_seconds=5.0).enrich(events)
    assert len([e for e in derived if e.event_type == TRACK_STABLE]) == 1


def test_multiple_tracks_are_independent():
    events = [
        _event("e1", "TrackLost", 0, track_id=1, timestamp_seconds=0.0),
        _event("e2", "TrackLost", 0, track_id=1, timestamp_seconds=0.5),
        _event("e3", "TrackUpdated", 0, track_id=2, timestamp_seconds=0.0),
        _event("e4", "TrackUpdated", 60, track_id=2, timestamp_seconds=6.0),
    ]
    derived = TrackStabilityEnricher(unstable_threshold_count=2, stable_duration_seconds=5.0).enrich(events)
    track_1 = [e for e in derived if e.track_id == 1]
    track_2 = [e for e in derived if e.track_id == 2]
    assert any(e.event_type == TRACK_UNSTABLE for e in track_1)
    assert any(e.event_type == TRACK_STABLE for e in track_2)


def test_events_without_track_id_are_ignored():
    events = [
        {
            "event_id": "e1",
            "event_type": "TrackLost",
            "frame_index": 0,
            "timestamp_seconds": 0.0,
            "track_id": None,
            "entity": None,
            "confidence": None,
            "position": None,
            "metadata": {},
            "parent_event_id": None,
        }
    ]
    assert TrackStabilityEnricher().enrich(events) == []
