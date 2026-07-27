"""Testes de worker.cognitive_runner.runner.run_cognitive_core (Phase 2,
G2A) - essencial.

Não mocka nenhuma camada do Cognitive Core: roda a cadeia real
(TimelineExplorer -> PlaySegmenter -> EnrichmentPipeline ->
build_temporal_memory -> build_working_state -> build_hypotheses ->
update_convictions -> build_plans -> decide -> evaluate) sobre um
event_timeline sintético, no formato real de `Event.to_dict()`."""
from __future__ import annotations

from uuid import uuid4

from worker.cognitive_runner.runner import run_cognitive_core
from worker.timeline import event_types


def _event(event_type: str, frame_index: int, timestamp_seconds: float, metadata: dict | None = None) -> dict:
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds,
        "track_id": 1,
        "entity": "person",
        "position": None,
        "confidence": None,
        "metadata": metadata or {},
        "parent_event_id": None,
    }


def _cluster(base_frame: int, start_timestamp: float) -> list[dict]:
    """3 eventos: TrackStarted (abre o segmento) + ObjectStopped (deixa o
    track_id 1 "parado" nesta janela) + TrackUpdated (mantém o segmento
    aberto até o frame do ObjectStopped, já que só eventos de conteúdo -
    TrackStarted/TrackUpdated/ObjectDetected/TrackRecovered - decidem os
    limites do segmento na GapStrategy, W30)."""
    return [
        _event(event_types.TRACK_STARTED, base_frame, start_timestamp),
        _event(event_types.OBJECT_STOPPED, base_frame + 1, start_timestamp + 0.05, metadata={"motion_state": "stopped"}),
        _event(event_types.TRACK_UPDATED, base_frame + 2, start_timestamp + 0.1),
    ]


def _single_segment_timeline() -> list[dict]:
    """1 cluster = 1 PlaySegment (nenhum gap > 1.0s dentro dele)."""
    return _cluster(base_frame=0, start_timestamp=0.0)


def _three_segment_timeline() -> list[dict]:
    """3 clusters, cada um separado por ~10s (> 1.0s, limiar padrão da
    GapStrategy) - produz exatamente 3 PlaySegments. O mesmo track_id=1
    aparece parado em cada um, permitindo observar o ConvictionSet
    acumulando observações consecutivas ENTRE segmentos."""
    events: list[dict] = []
    for cluster_index, start_timestamp in enumerate((0.0, 10.0, 20.0)):
        events.extend(_cluster(base_frame=cluster_index * 100, start_timestamp=start_timestamp))
    return events


def test_runner_executes_over_a_real_timeline():
    """Roda a cadeia inteira, sem mock de nenhuma função do núcleo, e
    confirma que o resultado é uma list[dict] no formato esperado -
    nunca uma dataclass nova (nenhum contrato novo é inventado)."""
    results = run_cognitive_core(_single_segment_timeline())

    assert isinstance(results, list)
    assert len(results) == 1
    result = results[0]
    assert set(result.keys()) == {"segment_id", "start_frame", "end_frame", "decision_set", "evaluation_set"}
    assert isinstance(result["decision_set"], dict)
    assert isinstance(result["evaluation_set"], dict)
    assert set(result["decision_set"].keys()) == {
        "track_decisions",
        "entity_decisions",
        "observed_at_frame",
        "observed_at_timestamp",
    }
    assert set(result["evaluation_set"].keys()) == {
        "track_evaluations",
        "entity_evaluations",
        "observed_at_frame",
        "observed_at_timestamp",
    }


def test_determinism_same_event_timeline_produces_same_result():
    """`segment_id` é um `uuid4()` novo a cada chamada (comportamento já
    existente de `PlaySegmenter`, W30, fora do escopo desta sprint) -
    determinismo aqui significa que o CONTEÚDO (fronteiras e
    decisão/avaliação por segmento) é sempre o mesmo, não o identificador
    aleatório."""
    event_timeline = _three_segment_timeline()
    first = run_cognitive_core(event_timeline)
    second = run_cognitive_core(event_timeline)

    def _without_segment_id(results: list[dict]) -> list[dict]:
        return [{k: v for k, v in result.items() if k != "segment_id"} for result in results]

    assert _without_segment_id(first) == _without_segment_id(second)


def test_multiple_play_segments_produce_multiple_results():
    results = run_cognitive_core(_three_segment_timeline())

    assert len(results) == 3
    assert len({r["segment_id"] for r in results}) == 3  # todos distintos
    assert [r["start_frame"] for r in results] == sorted(r["start_frame"] for r in results)  # ordem cronologica


def test_conviction_evolves_across_segments_and_eventually_produces_a_decision():
    """Um TrackPlan/TrackDecision só nasce para o track 1 no 3º segmento
    se o ConvictionSet foi ENCADEADO entre os 3 segmentos - o nível
    STABLE exige 3 observações consecutivas (W35), e cada WorkingState é
    reconstruído do zero por segmento (Seção 3 do plano aprovado). Se o
    runner reinicializasse ConvictionSet a cada segmento, isso nunca
    aconteceria."""
    results = run_cognitive_core(_three_segment_timeline())

    # 1a e 2a observacoes: conviction ainda EMERGING (limiar STABLE=3) -
    # Planning nao produz nenhum plano ainda.
    assert results[0]["decision_set"]["track_decisions"] == {}
    assert results[1]["decision_set"]["track_decisions"] == {}

    # 3a observacao consecutiva: conviction cruza para STABLE - Decision
    # produz exatamente uma decisao para o track 1.
    third_decisions = results[2]["decision_set"]["track_decisions"]
    assert 1 in third_decisions
    assert third_decisions[1]["plan_type"] == "engage"


def test_decision_set_is_produced_with_real_content():
    results = run_cognitive_core(_three_segment_timeline())
    decision = results[2]["decision_set"]["track_decisions"][1]
    assert decision["selected_plan_id"] == "engage:track:1"
    assert decision["winning_criteria"] == ["only_candidate"]
    assert decision["discarded_plan_ids"] == []


def test_evaluation_set_is_produced_with_real_content():
    results = run_cognitive_core(_three_segment_timeline())
    evaluation = results[2]["evaluation_set"]["track_evaluations"][1]
    assert evaluation["resolution_method"] == "single_candidate"
