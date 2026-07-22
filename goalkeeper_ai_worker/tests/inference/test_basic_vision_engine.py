"""Testes de worker.inference.basic_vision_engine.BasicVisionEngine.

Todos usam vídeos reais gerados com OpenCV (nunca mockados) - frame
skipping, resize, ROI, metadados, timestamps, resoluções diferentes,
vídeos curtos/longos e vídeos sem frames válidos."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.basic_vision_engine import BasicVisionEngine
from worker.inference.exceptions import InferenceExecutionError
from worker.state.pipeline_state import PipelineState


def _make_video(
    tmp_path: Path, frame_count: int, width: int = 64, height: int = 48, fps: float = 10.0
) -> Path:
    path = tmp_path / f"video_{frame_count}_{width}x{height}.avi"
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    for i in range(frame_count):
        frame = np.full((height, width, 3), i * 10 % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def _make_state(tmp_path: Path, video_path: Path) -> PipelineState:
    state = PipelineState(
        job_id="job-1", video_id="video-1", message_id="0-1", started_at=datetime.now(timezone.utc)
    )
    state.workspace_dir = tmp_path
    download_path = tmp_path / "input_video"
    shutil.copy(video_path, download_path)
    state.download_path = download_path
    return state


async def test_processes_every_frame_by_default(tmp_path: Path) -> None:
    video = _make_video(tmp_path, frame_count=10)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frames_processed == 10
    assert result.inference_result.frame_metadata.frame_count == 10
    assert result.inference_result.frame_skip == 0


async def test_frame_skip_reduces_frames_processed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORKER_FRAME_SKIP", "1")
    get_settings.cache_clear()
    video = _make_video(tmp_path, frame_count=10)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    # frame_skip=1 -> processa indices 0,2,4,6,8 = 5 dos 10 frames
    assert result.inference_result.frames_processed == 5
    assert result.inference_result.frame_metadata.frame_count == 10
    assert result.inference_result.frame_skip == 1


async def test_resize_changes_reported_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "true")
    monkeypatch.setenv("WORKER_TARGET_WIDTH", "32")
    monkeypatch.setenv("WORKER_TARGET_HEIGHT", "24")
    get_settings.cache_clear()
    video = _make_video(tmp_path, frame_count=5, width=64, height=48)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frame_metadata.width == 32
    assert result.inference_result.frame_metadata.height == 24


async def test_roi_changes_reported_resolution_and_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORKER_ENABLE_ROI", "true")
    monkeypatch.setenv("WORKER_ROI_X", "5")
    monkeypatch.setenv("WORKER_ROI_Y", "5")
    monkeypatch.setenv("WORKER_ROI_WIDTH", "20")
    monkeypatch.setenv("WORKER_ROI_HEIGHT", "15")
    get_settings.cache_clear()
    video = _make_video(tmp_path, frame_count=5, width=64, height=48)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frame_metadata.width == 20
    assert result.inference_result.frame_metadata.height == 15
    assert result.inference_result.roi is not None
    assert result.inference_result.roi.x == 5
    assert result.inference_result.roi.width == 20


async def test_metadata_and_timestamps_reflect_real_video(tmp_path: Path) -> None:
    video = _make_video(tmp_path, frame_count=20, fps=10.0)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frame_metadata.fps == pytest.approx(10.0, rel=0.1)
    assert result.inference_result.frame_metadata.duration_seconds == pytest.approx(2.0, rel=0.2)


async def test_handles_short_video(tmp_path: Path) -> None:
    video = _make_video(tmp_path, frame_count=1)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frames_processed == 1


async def test_handles_longer_video(tmp_path: Path) -> None:
    video = _make_video(tmp_path, frame_count=100)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frames_processed == 100


async def test_different_resolutions(tmp_path: Path) -> None:
    video = _make_video(tmp_path, frame_count=5, width=128, height=96)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frame_metadata.width == 128
    assert result.inference_result.frame_metadata.height == 96


async def test_raises_for_video_with_no_valid_frames(
    tmp_path: Path, corrupted_video_path: Path
) -> None:
    state = _make_state(tmp_path, corrupted_video_path)

    with pytest.raises(InferenceExecutionError):
        await BasicVisionEngine(get_settings()).process(state)


async def test_artifact_json_matches_expected_shape(tmp_path: Path) -> None:
    video = _make_video(tmp_path, frame_count=10)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["metadata"]["engine_name"] == "basic_vision"
    assert saved["frame_metadata"]["frame_count"] == 10
    assert saved["frames_processed"] == 10
    assert saved["frame_skip"] == 0
    assert saved["roi"] is None
    assert saved["detection_results"] == []


async def test_engine_is_a_thin_orchestrator_over_the_processor_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa: BasicVisionEngine nao transforma nada por conta
    propria - delega tudo a PipelineProcessor, e o artefato reflete as
    metricas reais de cada Processor executado."""
    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "true")
    monkeypatch.setenv("WORKER_TARGET_WIDTH", "16")
    monkeypatch.setenv("WORKER_TARGET_HEIGHT", "12")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=10)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    assert result.inference_result.frame_metadata.width == 16
    assert result.inference_result.frame_metadata.height == 12

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == ["color", "resize", "statistics"]
    assert saved["processors"]["color"]["frames_processed"] == 10
    assert saved["processors"]["resize"]["frames_processed"] == 10
    assert saved["processors"]["statistics"]["frames_processed"] == 10
    assert "roi" not in saved["processors"]


async def test_engine_with_yolo_processor_enabled_produces_real_detection_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com o Detector REAL (YOLO11n, sem mock) -
    BasicVisionEngine continua sem saber nada de Ultralytics/pesos/
    modelo: so le context.detections de volta, exatamente como ja lia
    context.stats desde a W7."""
    monkeypatch.setenv("WORKER_DETECTOR", "yolo")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=3)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == ["color", "statistics", "yolo"]
    assert saved["processors"]["yolo"]["frames_processed"] == 3
    assert len(saved["detection_results"]) == 3
    assert [entry["frame_index"] for entry in saved["detection_results"]] == [0, 1, 2]


async def test_engine_with_tracking_enabled_keeps_a_stable_track_id_across_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com o Tracker REAL (ByteTrack, sem mock) -
    mocka so a inferencia do Detector (um objeto se movendo levemente
    entre frames), prova que a mesma pessoa mantem o mesmo TrackId do
    inicio ao fim, exatamente como a validacao manual da W9 exige."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingObjectDetector(Detector):
        name = "moving-object-stub"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 10 + self._call_count * 2
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=x, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("moving-object-stub", _MovingObjectDetector)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-object-stub")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == ["color", "statistics", "yolo", "tracking"]
    assert saved["tracking_engine"] == "bytetrack"
    assert len(saved["tracking_results"]) == 5

    track_ids = {
        obj["track_id"]
        for entry in saved["tracking_results"]
        for obj in entry["tracked_objects"]
    }
    assert track_ids == {1}, f"esperava um unico TrackId estavel, obteve {track_ids}"

    ages = [entry["tracked_objects"][0]["age"] for entry in saved["tracking_results"]]
    assert ages == [1, 2, 3, 4, 5]

    frame_indexes = [entry["tracked_objects"][0]["frame_index"] for entry in saved["tracking_results"]]
    assert frame_indexes == [0, 1, 2, 3, 4]

    assert saved["tracking_statistics"]["total_tracks"] == 1
    assert saved["tracking_time_ms"] >= 0.0


async def test_engine_resets_tracker_state_between_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mesma instancia de BasicVisionEngine (e da PipelineProcessor que
    ela contem) e reaproveitada entre Jobs pelo WorkerOrchestrator - sem
    um reset explicito no inicio de process(), o Tracker vazaria
    TrackIds de um video para o proximo."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _FixedObjectDetector(Detector):
        name = "fixed-object-stub"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("fixed-object-stub", _FixedObjectDetector)

    monkeypatch.setenv("WORKER_DETECTOR", "fixed-object-stub")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    engine = BasicVisionEngine(settings)  # UMA instancia, reaproveitada nos dois Jobs abaixo

    video_a = _make_video(tmp_path, frame_count=3)
    state_a = _make_state(tmp_path, video_a)
    result_a = await engine.process(state_a)
    saved_a = json.loads(result_a.artifact_path.read_text(encoding="utf-8"))
    ages_a = [entry["tracked_objects"][0]["age"] for entry in saved_a["tracking_results"]]

    video_b = _make_video(tmp_path, frame_count=3)
    state_b = _make_state(tmp_path, video_b)
    result_b = await engine.process(state_b)
    saved_b = json.loads(result_b.artifact_path.read_text(encoding="utf-8"))
    ages_b = [entry["tracked_objects"][0]["age"] for entry in saved_b["tracking_results"]]

    assert ages_a == [1, 2, 3]
    assert ages_b == [1, 2, 3]  # reinicia do zero, nao continua [4, 5, 6]


async def test_engine_with_scene_analysis_enabled_produces_coherent_scene_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com o Tracker e o SceneAnalyzer REAIS (sem
    mock) - mocka so a inferencia do Detector (um objeto se movendo),
    prova que o artefato contem SceneEvents coerentes: TRACK_STARTED no
    primeiro frame, TRACK_UPDATED nos seguintes, estatisticas corretas."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingObjectDetector(Detector):
        name = "moving-object-stub-w10"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 10 + self._call_count * 2
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=x, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("moving-object-stub-w10", _MovingObjectDetector)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-object-stub-w10")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == ["color", "statistics", "yolo", "tracking", "scene_analysis"]

    event_types = [event["event_type"] for event in saved["scene_events"]]
    assert "track_started" in event_types
    assert "object_entered_frame" in event_types
    assert event_types.count("track_started") == 1  # so uma vez, no primeiro frame

    track_ids = {event["track_id"] for event in saved["scene_events"]}
    assert track_ids == {1}  # coerente com o TrackId estavel do Tracker

    assert saved["scene_statistics"]["total_tracks_observed"] == 1
    assert saved["scene_statistics"]["total_events"] == len(saved["scene_events"])
    assert saved["scene_processing_time_ms"] >= 0.0


async def test_engine_resets_scene_analyzer_state_between_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesmo achado arquitetural da W9 (Tracker), agora para o
    SceneAnalyzer: a mesma instancia de BasicVisionEngine e reaproveitada
    entre Jobs - sem reset, TRACK_STARTED so apareceria uma vez, nunca
    mais no segundo video."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _FixedObjectDetectorW10(Detector):
        name = "fixed-object-stub-w10"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("fixed-object-stub-w10", _FixedObjectDetectorW10)

    monkeypatch.setenv("WORKER_DETECTOR", "fixed-object-stub-w10")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    engine = BasicVisionEngine(settings)  # UMA instancia, reaproveitada nos dois Jobs abaixo

    video_a = _make_video(tmp_path, frame_count=2)
    state_a = _make_state(tmp_path, video_a)
    result_a = await engine.process(state_a)
    saved_a = json.loads(result_a.artifact_path.read_text(encoding="utf-8"))

    video_b = _make_video(tmp_path, frame_count=2)
    state_b = _make_state(tmp_path, video_b)
    result_b = await engine.process(state_b)
    saved_b = json.loads(result_b.artifact_path.read_text(encoding="utf-8"))

    event_types_a = [event["event_type"] for event in saved_a["scene_events"]]
    event_types_b = [event["event_type"] for event in saved_b["scene_events"]]

    assert "track_started" in event_types_a
    assert "track_started" in event_types_b  # reinicia - nao "ja vi essa trilha antes"
