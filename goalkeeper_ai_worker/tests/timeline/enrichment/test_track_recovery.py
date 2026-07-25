"""Testes de worker.timeline.enrichment.enrichers.track_recovery.
TrackRecoveryConfidenceEnricher."""
from __future__ import annotations

from worker.timeline.enrichment.enrichers.track_recovery import TrackRecoveryConfidenceEnricher
from worker.timeline.enrichment.event_types import TRACK_RECOVERED_WITH_CONFIDENCE


def _detected(event_id: str, frame_index: int, entity: str, confidence: float) -> dict:
    return {
        "event_id": event_id,
        "event_type": "ObjectDetected",
        "frame_index": frame_index,
        "timestamp_seconds": frame_index * 0.1,
        "track_id": None,
        "entity": entity,
        "confidence": confidence,
        "position": {"x": 1.0, "y": 2.0},
        "metadata": {},
        "parent_event_id": None,
    }


def _recovered(event_id: str, frame_index: int, track_id: int, entity: str) -> dict:
    return {
        "event_id": event_id,
        "event_type": "TrackRecovered",
        "frame_index": frame_index,
        "timestamp_seconds": frame_index * 0.1,
        "track_id": track_id,
        "entity": entity,
        "confidence": None,
        "position": None,
        "metadata": {},
        "parent_event_id": None,
    }


def test_no_events_produces_no_derived_events():
    assert TrackRecoveryConfidenceEnricher().enrich([]) == []


def test_matching_detection_in_the_same_frame_produces_confidence_event():
    events = [
        _detected("e1", 10, entity="sports ball", confidence=0.75),
        _recovered("e2", 10, track_id=1, entity="sports ball"),
    ]
    derived = TrackRecoveryConfidenceEnricher().enrich(events)
    assert len(derived) == 1
    assert derived[0].event_type == TRACK_RECOVERED_WITH_CONFIDENCE
    assert derived[0].confidence == 0.75
    assert derived[0].track_id == 1


def test_entity_is_normalized_for_correlation():
    """ObjectDetected diz 'ball' (normalizado); TrackRecovered diz 'sports
    ball' (rotulo bruto) - devem se correlacionar mesmo assim."""
    events = [
        _detected("e1", 10, entity="ball", confidence=0.6),
        _recovered("e2", 10, track_id=1, entity="sports ball"),
    ]
    derived = TrackRecoveryConfidenceEnricher().enrich(events)
    assert len(derived) == 1
    assert derived[0].confidence == 0.6


def test_provenance_references_both_source_events():
    events = [
        _detected("e1", 10, entity="ball", confidence=0.6),
        _recovered("e2", 10, track_id=1, entity="sports ball"),
    ]
    derived = TrackRecoveryConfidenceEnricher().enrich(events)
    assert derived[0].parent_event_id == "e2"  # TrackRecovered e o parent primario
    assert set(derived[0].metadata["provenance"]) == {"e1", "e2"}  # ambos preservados


def test_no_matching_detection_produces_no_event():
    events = [_recovered("e2", 10, track_id=1, entity="sports ball")]
    assert TrackRecoveryConfidenceEnricher().enrich(events) == []


def test_different_frame_does_not_correlate():
    events = [
        _detected("e1", 9, entity="sports ball", confidence=0.75),
        _recovered("e2", 10, track_id=1, entity="sports ball"),
    ]
    assert TrackRecoveryConfidenceEnricher().enrich(events) == []


def test_different_entity_does_not_correlate():
    events = [
        _detected("e1", 10, entity="person", confidence=0.9),
        _recovered("e2", 10, track_id=1, entity="sports ball"),
    ]
    assert TrackRecoveryConfidenceEnricher().enrich(events) == []


def test_multiple_candidates_picks_deterministic_first_match():
    events = [
        _detected("e1", 10, entity="sports ball", confidence=0.3),
        _detected("e2", 10, entity="sports ball", confidence=0.9),
        _recovered("e3", 10, track_id=1, entity="sports ball"),
    ]
    derived = TrackRecoveryConfidenceEnricher().enrich(events)
    assert derived[0].confidence == 0.3  # primeiro na ordem de events, nao o de maior confianca
