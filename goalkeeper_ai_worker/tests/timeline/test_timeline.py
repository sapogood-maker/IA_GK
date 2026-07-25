"""Testes de worker.timeline.timeline.PerceptionTimeline."""
from __future__ import annotations

from worker.timeline.event import Event
from worker.timeline.timeline import PerceptionTimeline


def _event(frame_index: int, event_type: str = "FrameProcessed") -> Event:
    return Event(
        event_type=event_type,
        frame_index=frame_index,
        timestamp_seconds=None,
        track_id=None,
        entity=None,
        position=None,
        confidence=None,
    )


def test_starts_empty():
    timeline = PerceptionTimeline()
    assert len(timeline) == 0
    assert list(timeline) == []


def test_append_adds_one_event():
    timeline = PerceptionTimeline()
    timeline.append(_event(0))
    assert len(timeline) == 1


def test_extend_adds_multiple_events():
    timeline = PerceptionTimeline()
    timeline.extend([_event(0), _event(1), _event(2)])
    assert len(timeline) == 3


def test_to_dict_is_ordered_by_frame_index_even_if_inserted_out_of_order():
    timeline = PerceptionTimeline()
    timeline.append(_event(2))
    timeline.append(_event(0))
    timeline.append(_event(1))

    frame_indexes = [entry["frame_index"] for entry in timeline.to_dict()]
    assert frame_indexes == [0, 1, 2]


def test_to_dict_is_stable_for_events_in_the_same_frame():
    timeline = PerceptionTimeline()
    timeline.append(_event(0, event_type="First"))
    timeline.append(_event(0, event_type="Second"))

    event_types = [entry["event_type"] for entry in timeline.to_dict()]
    assert event_types == ["First", "Second"]


def test_has_no_mutation_api_besides_append_and_extend():
    """Reforca a garantia de log imutavel/append-only - nao deve existir
    nenhum metodo publico de remover/substituir/editar um Event ja
    adicionado."""
    public_methods = {
        name for name in dir(PerceptionTimeline) if not name.startswith("_")
    }
    assert public_methods == {"append", "extend", "to_dict"}
