"""Testes de CognitiveRunnerStage (Phase 2, G2B/G2C/G2D) - mescla
`cognitive_core_result`/`cognitive_core_metrics`/`cognitive_core_summary`
no artifact.json ja existente, sem tocar em nenhuma outra chave, e nunca
propaga excecao (Stage observacional - plano de integracao aprovado, Secao
3-B)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

from worker.pipeline.stages.cognitive_runner import CognitiveRunnerStage
from worker.timeline import event_types


def _write_artifact(path: Path, extra_keys: dict) -> None:
    payload = {"status": "processed", "event_timeline": [], **extra_keys}
    path.write_text(json.dumps(payload), encoding="utf-8")


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


def _single_segment_timeline() -> list[dict]:
    return [
        _event(event_types.TRACK_STARTED, 0, 0.0),
        _event(event_types.OBJECT_STOPPED, 1, 0.05, metadata={"motion_state": "stopped"}),
        _event(event_types.TRACK_UPDATED, 2, 0.1),
    ]


async def test_happy_path_adds_cognitive_core_result_to_the_artifact(base_state, tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    _write_artifact(artifact_path, {})
    base_state.artifact_path = artifact_path
    base_state.event_timeline = []

    result = await CognitiveRunnerStage().run(base_state)

    assert result is base_state
    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert saved["cognitive_core_result"] == []


async def test_happy_path_also_adds_cognitive_core_metrics_and_summary(base_state, tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    _write_artifact(artifact_path, {})
    base_state.artifact_path = artifact_path
    base_state.event_timeline = []

    await CognitiveRunnerStage().run(base_state)

    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert set(saved["cognitive_core_metrics"].keys()) == {"counts", "timing_ms", "segments"}
    assert saved["cognitive_core_metrics"]["counts"]["play_segments"] == 0
    assert saved["cognitive_core_metrics"]["segments"] == []
    assert saved["cognitive_core_summary"]["total_segments"] == 0
    assert saved["cognitive_core_summary"]["decision_rate"] == 0.0


async def test_existing_artifact_keys_are_preserved_unchanged(base_state, tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    extra_keys = {
        "detection_results": [{"label": "ball", "confidence": 0.9}],
        "tracking_results": [{"track_id": 1}],
        "frames_processed": 10,
        "metadata": {"engine_name": "basic_vision"},
    }
    _write_artifact(artifact_path, extra_keys)
    before = json.loads(artifact_path.read_text(encoding="utf-8"))
    base_state.artifact_path = artifact_path
    base_state.event_timeline = []

    await CognitiveRunnerStage().run(base_state)

    after = json.loads(artifact_path.read_text(encoding="utf-8"))
    for key, value in before.items():
        assert after[key] == value
    assert set(after.keys()) == set(before.keys()) | {
        "cognitive_core_result", "cognitive_core_metrics", "cognitive_core_summary",
    }


async def test_failure_inside_the_runner_is_logged_and_never_propagates(
    base_state, tmp_path: Path, caplog
) -> None:
    """event_timeline=None faz TimelineExplorer/chronological() falhar
    (sorted(None, ...)) - uma falha real dentro da cadeia do Core, sem
    monkeypatch, sem alterar Runner/Core. A Stage deve engolir isso."""
    artifact_path = tmp_path / "artifact.json"
    _write_artifact(artifact_path, {})
    before = artifact_path.read_text(encoding="utf-8")
    base_state.artifact_path = artifact_path
    base_state.event_timeline = None

    with caplog.at_level(logging.ERROR):
        result = await CognitiveRunnerStage().run(base_state)

    assert result is base_state
    assert artifact_path.read_text(encoding="utf-8") == before  # artifact intocado

    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert base_state.job_id in record.getMessage()
    assert base_state.video_id in record.getMessage()
    assert record.exc_info is not None  # stacktrace presente (logger.exception)


async def test_failure_when_artifact_path_is_missing_is_also_swallowed(base_state) -> None:
    """state.artifact_path ainda None (ex.: Stage rodando fora de ordem) -
    tambem deve ser engolido, nunca derrubar o Job."""
    base_state.artifact_path = None
    base_state.event_timeline = []

    result = await CognitiveRunnerStage().run(base_state)

    assert result is base_state


async def test_the_cognitive_core_runs_exactly_once_per_job(base_state, tmp_path: Path, monkeypatch) -> None:
    """G2D: build_hypotheses() (uma das camadas do Core) deve ser chamada
    exatamente uma vez por PlaySegment (1 segmento neste fixture) - nunca
    duas, o que aconteceria se `cognitive_core_result` e
    `cognitive_core_metrics`/`summary` ainda viessem de duas execucoes
    separadas da cadeia (comportamento da G2C, eliminado nesta sprint)."""
    import worker.cognitive_runner.runner as runner_module

    call_count = {"n": 0}
    original_build_hypotheses = runner_module.build_hypotheses

    def _counting_build_hypotheses(working_state):
        call_count["n"] += 1
        return original_build_hypotheses(working_state)

    monkeypatch.setattr(runner_module, "build_hypotheses", _counting_build_hypotheses)

    artifact_path = tmp_path / "artifact.json"
    _write_artifact(artifact_path, {})
    base_state.artifact_path = artifact_path
    base_state.event_timeline = _single_segment_timeline()

    await CognitiveRunnerStage().run(base_state)

    assert call_count["n"] == 1  # 1 PlaySegment neste fixture - nao 2
