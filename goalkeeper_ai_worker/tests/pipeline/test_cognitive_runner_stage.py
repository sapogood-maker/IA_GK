"""Testes de CognitiveRunnerStage (Phase 2, G2B) - mescla `cognitive_core_result`
no artifact.json ja existente, sem tocar em nenhuma outra chave, e nunca
propaga excecao (Stage observacional - plano de integracao aprovado, Secao
3-B)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from worker.pipeline.stages.cognitive_runner import CognitiveRunnerStage


def _write_artifact(path: Path, extra_keys: dict) -> None:
    payload = {"status": "processed", "event_timeline": [], **extra_keys}
    path.write_text(json.dumps(payload), encoding="utf-8")


async def test_happy_path_adds_cognitive_core_result_to_the_artifact(base_state, tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    _write_artifact(artifact_path, {})
    base_state.artifact_path = artifact_path
    base_state.event_timeline = []

    result = await CognitiveRunnerStage().run(base_state)

    assert result is base_state
    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert saved["cognitive_core_result"] == []


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
    assert set(after.keys()) == set(before.keys()) | {"cognitive_core_result"}


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
