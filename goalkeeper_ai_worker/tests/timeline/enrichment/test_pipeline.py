"""Testes de worker.timeline.enrichment.pipeline.EnrichmentPipeline -
usa Enrichers stub (nao os reais) para isolar o comportamento de
ORQUESTRACAO do Pipeline em si: mesma entrada para todos, nenhum
encadeamento, saida ordenada e deterministica."""
from __future__ import annotations

from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.enrichment.pipeline import EnrichmentPipeline
from worker.timeline.event import Event


class _RecordingEnricher(Enricher):
    """Registra exatamente o `events` que recebeu, para provar que o
    Pipeline nao encadeia (repassa sempre a entrada ORIGINAL)."""

    def __init__(self, name: str, output_event_type: str) -> None:
        self.name = name
        self._output_event_type = output_event_type
        self.received_events: list[dict] | None = None

    def enrich(self, events: list[dict]) -> list[Event]:
        self.received_events = events
        return [
            Event(
                event_type=self._output_event_type,
                frame_index=0,
                timestamp_seconds=0.0,
                track_id=None,
                entity=None,
                position=None,
                confidence=None,
                metadata={"produced_by": self.name},
            )
        ]


def _raw_event(frame_index: int) -> dict:
    return {
        "event_id": f"raw-{frame_index}",
        "event_type": "FrameProcessed",
        "frame_index": frame_index,
        "timestamp_seconds": frame_index * 0.1,
        "track_id": None,
        "entity": None,
        "confidence": None,
        "position": None,
        "metadata": {},
        "parent_event_id": None,
    }


def test_empty_enricher_list_produces_no_events():
    pipeline = EnrichmentPipeline([])
    assert pipeline.run([_raw_event(0)]) == []


def test_each_enricher_receives_the_same_original_input():
    events = [_raw_event(0), _raw_event(1)]
    enricher_a = _RecordingEnricher("a", "FakeA")
    enricher_b = _RecordingEnricher("b", "FakeB")

    EnrichmentPipeline([enricher_a, enricher_b]).run(events)

    assert enricher_a.received_events == events
    assert enricher_b.received_events == events
    # Mesma lista de objetos (identidade), nao so valores iguais - prova
    # que o Pipeline nao reconstroi/filtra o input por Enricher.
    assert enricher_a.received_events is enricher_b.received_events


def test_enrichers_never_see_each_others_derived_output():
    """Principio obrigatorio: nenhum Enricher consome a saida de outro
    nesta sprint. Prova indireta: o segundo Enricher so recebeu os
    eventos ORIGINAIS (sem nenhum FakeA dentro), mesmo rodando depois."""
    events = [_raw_event(0)]
    enricher_a = _RecordingEnricher("a", "FakeA")
    enricher_b = _RecordingEnricher("b", "FakeB")

    EnrichmentPipeline([enricher_a, enricher_b]).run(events)

    assert all(e["event_type"] != "FakeA" for e in enricher_b.received_events)
    assert enricher_b.received_events == events


def test_output_is_concatenated_from_all_enrichers():
    events = [_raw_event(0)]
    enricher_a = _RecordingEnricher("a", "FakeA")
    enricher_b = _RecordingEnricher("b", "FakeB")

    derived = EnrichmentPipeline([enricher_a, enricher_b]).run(events)

    assert {e.event_type for e in derived} == {"FakeA", "FakeB"}


def test_output_is_sorted_by_frame_index():
    class _FixedFrameEnricher(Enricher):
        name = "fixed"

        def __init__(self, frame_index: int, event_type: str) -> None:
            self._frame_index = frame_index
            self._event_type = event_type

        def enrich(self, events: list[dict]) -> list[Event]:
            return [
                Event(
                    event_type=self._event_type,
                    frame_index=self._frame_index,
                    timestamp_seconds=None,
                    track_id=None,
                    entity=None,
                    position=None,
                    confidence=None,
                )
            ]

    pipeline = EnrichmentPipeline([_FixedFrameEnricher(10, "Late"), _FixedFrameEnricher(1, "Early")])
    derived = pipeline.run([_raw_event(0)])

    assert [e.event_type for e in derived] == ["Early", "Late"]


def test_determinism_same_input_produces_same_output():
    events = [_raw_event(0), _raw_event(1)]
    pipeline = EnrichmentPipeline([_RecordingEnricher("a", "FakeA")])

    first = [e.to_dict() for e in pipeline.run(events)]
    second = [e.to_dict() for e in pipeline.run(events)]

    for a, b in zip(first, second):
        assert {k: v for k, v in a.items() if k != "event_id"} == {k: v for k, v in b.items() if k != "event_id"}
