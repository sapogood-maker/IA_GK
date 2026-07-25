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


async def test_engine_with_world_model_enabled_produces_a_coherent_world_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com o Tracker, SceneAnalyzer e WorldModel REAIS
    (sem mock) - mocka so a inferencia do Detector (um objeto se
    movendo), prova que o artefato contem um WorldState coerente: mesmo
    TrackId do inicio ao fim, idade/posicao/velocidade corretas."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingObjectDetectorW11(Detector):
        name = "moving-object-stub-w11"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 10 + self._call_count * 5
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=x, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("moving-object-stub-w11", _MovingObjectDetectorW11)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-object-stub-w11")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == [
        "color", "statistics", "yolo", "tracking", "scene_analysis", "world_model",
    ]

    world_state = saved["world_state"]
    assert world_state is not None
    assert len(world_state["active_objects"]) == 1
    active_object = world_state["active_objects"][0]
    assert active_object["track_id"] == 1
    assert active_object["age"] == 5
    assert active_object["frames_visible"] == 5
    assert active_object["motion"]["speed"] > 0  # objeto se moveu 5px/frame

    assert saved["object_count"] == 1
    assert saved["active_tracks"] == 1
    assert saved["lost_tracks"] == 0
    assert saved["average_speed"] > 0
    assert saved["processing_time_ms"] >= 0.0
    assert saved["world_statistics"]["object_count"] == 1


async def test_engine_resets_world_model_state_between_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesmo achado arquitetural da W9/W10, agora para o WorldModel: a
    mesma instancia de BasicVisionEngine e reaproveitada entre Jobs - sem
    reset, a idade do objeto continuaria acumulando entre videos
    diferentes em vez de reiniciar em 1."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _FixedObjectDetectorW11(Detector):
        name = "fixed-object-stub-w11"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("fixed-object-stub-w11", _FixedObjectDetectorW11)

    monkeypatch.setenv("WORKER_DETECTOR", "fixed-object-stub-w11")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    engine = BasicVisionEngine(settings)  # UMA instancia, reaproveitada nos dois Jobs abaixo

    video_a = _make_video(tmp_path, frame_count=3)
    state_a = _make_state(tmp_path, video_a)
    result_a = await engine.process(state_a)
    saved_a = json.loads(result_a.artifact_path.read_text(encoding="utf-8"))

    video_b = _make_video(tmp_path, frame_count=3)
    state_b = _make_state(tmp_path, video_b)
    result_b = await engine.process(state_b)
    saved_b = json.loads(result_b.artifact_path.read_text(encoding="utf-8"))

    age_a = saved_a["world_state"]["active_objects"][0]["age"]
    age_b = saved_b["world_state"]["active_objects"][0]["age"]

    assert age_a == 3
    assert age_b == 3  # reinicia do zero, nao continua 6


async def test_engine_with_football_domain_enabled_produces_a_coherent_football_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel REAIS (sem
    mock) - mocka so a inferencia do Detector (rotulo "goalkeeper"), prova
    que o artefato contem um FootballWorld coerente: o objeto rotulado
    goalkeeper aparece em world["goalkeepers"], nao em players/balls."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _GoalkeeperDetectorW12(Detector):
        name = "goalkeeper-stub-w12"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 10 + self._call_count * 5
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=x, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("goalkeeper-stub-w12", _GoalkeeperDetectorW12)

    monkeypatch.setenv("WORKER_DETECTOR", "goalkeeper-stub-w12")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == [
        "color", "statistics", "yolo", "tracking", "scene_analysis", "world_model", "football_domain",
    ]

    football_world = saved["football_world"]
    assert football_world is not None
    assert len(football_world["goalkeepers"]) == 1
    assert football_world["players"] == []
    assert football_world["balls"] == []

    goalkeeper = football_world["goalkeepers"][0]
    assert goalkeeper["age"] == 5
    assert goalkeeper["speed"] > 0  # objeto se moveu 5px/frame

    assert football_world["field"]["direction"] == "unknown"
    assert len(football_world["goals"]) == 2
    assert saved["football_domain_time_ms"] >= 0.0


async def test_engine_resets_football_domain_state_between_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesmo achado arquitetural da W9-W11, agora aplicado PROATIVAMENTE
    para o Football Domain Model: field/goals nao devem sobreviver entre
    Jobs - cada video deve ganhar sua PROPRIA instancia de Field."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _FixedGoalkeeperDetectorW12(Detector):
        name = "fixed-goalkeeper-stub-w12"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("fixed-goalkeeper-stub-w12", _FixedGoalkeeperDetectorW12)

    monkeypatch.setenv("WORKER_DETECTOR", "fixed-goalkeeper-stub-w12")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
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

    age_a = saved_a["football_world"]["goalkeepers"][0]["age"]
    age_b = saved_b["football_world"]["goalkeepers"][0]["age"]

    assert age_a == 2
    assert age_b == 2  # reinicia do zero, nao continua 4


async def test_engine_with_analyzers_enabled_produces_a_coherent_goalkeeper_presence_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka so a inferencia do Detector (rotulo
    "goalkeeper"), prova que o artefato contem um GoalkeeperPresenceResult
    coerente dentro de analysis_results."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _GoalkeeperDetectorW13(Detector):
        name = "goalkeeper-stub-w13"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 10 + self._call_count * 5
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=x, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("goalkeeper-stub-w13", _GoalkeeperDetectorW13)

    monkeypatch.setenv("WORKER_DETECTOR", "goalkeeper-stub-w13")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == [
        "color", "statistics", "yolo", "tracking", "scene_analysis",
        "world_model", "football_domain", "analyzer",
    ]

    assert saved["analysis_statistics"] == {
        "analyzers_run": ["goalkeeper_presence"], "results_count": 1,
    }

    presence = saved["analysis_results"]["goalkeeper_presence"]
    assert presence["exists"] is True
    assert presence["visible"] is True
    assert presence["goalkeeper_count"] == 1
    assert presence["track_id"] == 1
    assert presence["age"] == 5
    assert presence["current_position"] is not None
    assert presence["current_bbox"] is not None


async def test_engine_resets_analyzer_state_between_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesmo achado arquitetural da W9-W12, agora para a Analyzer API: a
    mesma instancia de BasicVisionEngine e reaproveitada entre Jobs - sem
    reset, a idade do goleiro reportada continuaria acumulando entre
    videos diferentes em vez de reiniciar."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _FixedGoalkeeperDetectorW13(Detector):
        name = "fixed-goalkeeper-stub-w13"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("fixed-goalkeeper-stub-w13", _FixedGoalkeeperDetectorW13)

    monkeypatch.setenv("WORKER_DETECTOR", "fixed-goalkeeper-stub-w13")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence")
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

    age_a = saved_a["analysis_results"]["goalkeeper_presence"]["age"]
    age_b = saved_b["analysis_results"]["goalkeeper_presence"]["age"]

    assert age_a == 2
    assert age_b == 2  # reinicia do zero, nao continua 4


async def test_engine_with_goal_geometry_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - o Goal e construido pelo FootballWorldBuilder
    independente de qualquer deteccao (Field/Goal sao sempre criados na
    primeira chamada de build()), entao um Detector sem deteccoes basta
    para provar que o artefato contem um GoalGeometryResult coerente."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import DetectionResult

    class _EmptyDetectorW14(Detector):
        name = "empty-stub-w14"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            return DetectionResult(detections=[])

    register_detector("empty-stub-w14", _EmptyDetectorW14)

    monkeypatch.setenv("WORKER_DETECTOR", "empty-stub-w14")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence,goal_geometry")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=3)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["processor_order"] == [
        "color", "statistics", "yolo", "tracking", "scene_analysis",
        "world_model", "football_domain", "analyzer",
    ]

    geometry = saved["goal_geometry_result"]
    assert geometry is not None
    assert geometry["goal_detected"] is True
    assert geometry["goal_width"] > 0
    assert geometry["goal_height"] > 0
    assert geometry["confidence"] == 1.0
    assert set(geometry["goal_regions"].keys()) == {
        "top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right",
    }
    assert saved["analysis_results"]["goal_geometry"] == geometry
    assert saved["analysis_statistics"]["analyzers_run"] == ["goal_geometry", "goalkeeper_presence"]


async def test_engine_with_goalkeeper_position_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka so a inferencia do Detector (rotulo
    "goalkeeper"). WORKER_ANALYZERS inclui APENAS "goalkeeper_position"
    (nao "goal_geometry") - prova que a composicao interna (W14/W15)
    funciona mesmo sem o outro Analyzer estar registrado como ativo na
    pipeline, ja que GoalkeeperPositionAnalyzer instancia seu proprio
    GoalGeometryAnalyzer."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _GoalkeeperDetectorW15(Detector):
        name = "goalkeeper-stub-w15"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.8),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            return DetectionResult(detections=[detection])

    register_detector("goalkeeper-stub-w15", _GoalkeeperDetectorW15)

    monkeypatch.setenv("WORKER_DETECTOR", "goalkeeper-stub-w15")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_position")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=3)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    position = saved["goalkeeper_position_result"]
    assert position is not None
    assert position["goalkeeper_detected"] is True
    assert position["goal_detected"] is True
    assert position["distance_to_goal_center"] > 0
    assert position["angle_to_goal"] is not None
    assert position["confidence"] is not None
    assert saved["analysis_results"]["goalkeeper_position"] == position
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_position"]


async def test_engine_with_ball_position_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka so a inferencia do Detector (rotulo
    "sports ball"). WORKER_ANALYZERS inclui APENAS "ball_position" (nao
    "goal_geometry") - prova que a composicao interna (W14/W15/W16)
    funciona mesmo sem o outro Analyzer estar registrado como ativo na
    pipeline, ja que BallPositionAnalyzer instancia seu proprio
    GoalGeometryAnalyzer."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _BallDetectorW16(Detector):
        name = "ball-stub-w16"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=10, y=10, width=10, height=10),
            )
            return DetectionResult(detections=[detection])

    register_detector("ball-stub-w16", _BallDetectorW16)

    monkeypatch.setenv("WORKER_DETECTOR", "ball-stub-w16")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "ball_position")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=3)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    position = saved["ball_position_result"]
    assert position is not None
    assert position["ball_detected"] is True
    assert position["goal_detected"] is True
    assert position["distance_to_goal_center"] > 0
    assert position["angle_to_goal"] is not None
    assert position["confidence"] is not None
    assert saved["analysis_results"]["ball_position"] == position
    assert saved["analysis_statistics"]["analyzers_run"] == ["ball_position"]


async def test_engine_with_goalkeeper_ball_alignment_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (rotulos "goalkeeper" e "sports ball", em posicoes
    fixas distintas). WORKER_ANALYZERS inclui APENAS
    "goalkeeper_ball_alignment" (nem goal_geometry, nem
    goalkeeper_position, nem ball_position) - prova que a composicao
    tripla (W14/W15/W16 reunidas) funciona mesmo sem nenhum dos tres
    Analyzers compostos estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _GoalkeeperAndBallDetectorW17(Detector):
        name = "goalkeeper-and-ball-stub-w17"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=100, y=10, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("goalkeeper-and-ball-stub-w17", _GoalkeeperAndBallDetectorW17)

    monkeypatch.setenv("WORKER_DETECTOR", "goalkeeper-and-ball-stub-w17")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_ball_alignment")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=3)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    alignment = saved["goalkeeper_ball_alignment_result"]
    assert alignment is not None
    assert alignment["goalkeeper_detected"] is True
    assert alignment["ball_detected"] is True
    assert alignment["goal_detected"] is True
    assert alignment["goalkeeper_to_ball_distance"] > 0
    assert alignment["ball_to_goal_distance"] > 0
    assert alignment["goalkeeper_to_goal_distance"] > 0
    assert alignment["alignment_line"] is not None
    assert alignment["is_between_ball_and_goal"] in (True, False)
    assert alignment["confidence"] is not None
    assert saved["analysis_results"]["goalkeeper_ball_alignment"] == alignment
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_ball_alignment"]


async def test_engine_with_ball_motion_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka so a inferencia do Detector (bola real se
    movendo 5px/frame, mesmo track_id do inicio ao fim), prova que o
    artefato contem um BallMotionResult coerente com o movimento real."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingBallDetectorW18(Detector):
        name = "moving-ball-stub-w18"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 10 + self._call_count * 5
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=x, y=10, width=10, height=10),
            )
            return DetectionResult(detections=[detection])

    register_detector("moving-ball-stub-w18", _MovingBallDetectorW18)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-ball-stub-w18")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "ball_motion")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    motion = saved["ball_motion_result"]
    assert motion is not None
    assert motion["ball_detected"] is True
    assert motion["frames_observed"] == 5
    assert motion["displacement"] == 5.0
    assert motion["speed"] == 5.0
    assert motion["motion_detected"] is True
    assert motion["stationary"] is False
    # ByteTrack aplica suavizacao de Kalman sobre a caixa delimitadora,
    # entao a velocidade entre frames consecutivos nao e EXATAMENTE
    # identica mesmo com passo fixo de 5px/frame no stub - so confirmamos
    # que a aceleracao foi calculada (nao None) e e pequena.
    assert motion["acceleration"] is not None
    assert abs(motion["acceleration"]) < 2.0
    assert motion["confidence"] is not None
    assert saved["analysis_results"]["ball_motion"] == motion
    assert saved["analysis_statistics"]["analyzers_run"] == ["ball_motion"]


async def test_engine_resets_ball_motion_state_between_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesmo achado arquitetural da W9-W17, agora para o primeiro Analyzer
    STATEFUL: a mesma instancia de BasicVisionEngine e reaproveitada entre
    Jobs - sem reset, frames_observed/previous_position continuariam
    acumulando entre videos diferentes em vez de reiniciar."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _FixedBallDetectorW18(Detector):
        name = "fixed-ball-stub-w18"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def detect(self, frame) -> DetectionResult:
            detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=10, y=10, width=10, height=10),
            )
            return DetectionResult(detections=[detection])

    register_detector("fixed-ball-stub-w18", _FixedBallDetectorW18)

    monkeypatch.setenv("WORKER_DETECTOR", "fixed-ball-stub-w18")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "ball_motion")
    get_settings.cache_clear()
    settings = get_settings()

    engine = BasicVisionEngine(settings)  # UMA instancia, reaproveitada nos dois Jobs abaixo

    video_a = _make_video(tmp_path, frame_count=3)
    state_a = _make_state(tmp_path, video_a)
    result_a = await engine.process(state_a)
    saved_a = json.loads(result_a.artifact_path.read_text(encoding="utf-8"))

    video_b = _make_video(tmp_path, frame_count=3)
    state_b = _make_state(tmp_path, video_b)
    result_b = await engine.process(state_b)
    saved_b = json.loads(result_b.artifact_path.read_text(encoding="utf-8"))

    frames_observed_a = saved_a["ball_motion_result"]["frames_observed"]
    frames_observed_b = saved_b["ball_motion_result"]["frames_observed"]

    assert frames_observed_a == 3
    assert frames_observed_b == 3  # reinicia do zero, nao continua 6
    assert saved_b["ball_motion_result"]["previous_position"] is not None  # comparou dentro do proprio video B


async def test_engine_with_shot_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka so a inferencia do Detector (bola real se
    movendo 5px/frame em direcao decrescente de x, mesmo track_id do
    inicio ao fim - o gol placeholder do FootballWorldBuilder fica perto
    de x=0, entao mover em -x e "em direcao ao gol"). WORKER_SHOT_MIN_SPEED
    e reduzido para um valor compativel com o passo de 5px/frame do stub
    (o mesmo padrao ja usado nos testes de Ball Motion/Position), provando
    que os limiares sao de fato parametrizaveis via configuracao."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _ShootingBallDetectorW19(Detector):
        name = "shooting-ball-stub-w19"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 300 - self._call_count * 5
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[detection])

    register_detector("shooting-ball-stub-w19", _ShootingBallDetectorW19)

    monkeypatch.setenv("WORKER_DETECTOR", "shooting-ball-stub-w19")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "shot")
    monkeypatch.setenv("WORKER_SHOT_MIN_SPEED", "3.0")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    shot = saved["shot_analysis_result"]
    assert shot is not None
    assert shot["ball_detected"] is True
    assert shot["motion_detected"] is True
    assert shot["ball_speed"] is not None and shot["ball_speed"] > 0
    # "towards_goal"/"shot_detected" dependem de comparar a direcao real
    # (em pixels) contra o centro do gol placeholder (geometria
    # normalizada 0-1, Risco 22/34) - os dois espacos de coordenada nao
    # sao calibrados entre si nesta camada, entao o valor exato de
    # towards_goal depende da geometria sintetica do video de teste; a
    # logica geometrica exata (com coordenadas totalmente controladas) ja
    # e coberta por tests/analyzers/test_shot.py. Aqui so confirmamos que
    # os campos existem e sao do tipo esperado - a integracao real.
    assert isinstance(shot["towards_goal"], bool)
    assert isinstance(shot["shot_detected"], bool)
    assert shot["observation_count"] == 5
    assert shot["confidence"] is not None
    assert saved["analysis_results"]["shot"] == shot
    assert saved["analysis_statistics"]["analyzers_run"] == ["shot"]


async def test_engine_with_ball_trajectory_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka so a inferencia do Detector (bola real se
    movendo 5px/frame em linha reta, mesmo track_id do inicio ao fim).
    WORKER_ANALYZERS inclui APENAS "ball_trajectory" - prova que a
    composicao interna (W14/W16/W18) funciona mesmo sem os outros
    Analyzers estarem ativos na mesma lista."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _StraightLineBallDetectorW20(Detector):
        name = "straight-line-ball-stub-w20"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            x = 300 - self._call_count * 5
            self._call_count += 1
            detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[detection])

    register_detector("straight-line-ball-stub-w20", _StraightLineBallDetectorW20)

    monkeypatch.setenv("WORKER_DETECTOR", "straight-line-ball-stub-w20")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "ball_trajectory")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    trajectory = saved["ball_trajectory_result"]
    assert trajectory is not None
    assert trajectory["ball_detected"] is True
    assert trajectory["trajectory_detected"] is True
    assert trajectory["frames_observed"] == 5
    assert len(trajectory["trajectory_points"]) == 5
    assert trajectory["trajectory_length"] is not None and trajectory["trajectory_length"] > 0
    assert trajectory["linearity_score"] is not None
    assert trajectory["direction_consistency"] is not None
    assert trajectory["confidence"] is not None
    assert saved["analysis_results"]["ball_trajectory"] == trajectory
    assert saved["analysis_statistics"]["analyzers_run"] == ["ball_trajectory"]


async def test_engine_with_play_situation_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro parado + bola se movendo 5px/frame em
    linha reta, mesmo track_id do inicio ao fim). WORKER_ANALYZERS inclui
    APENAS "play_situation" - prova que a composicao QUADRUPLA (W17/W19/
    W20 reunidas) funciona mesmo sem nenhum dos quatro Analyzers
    compostos estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _GoalkeeperAndMovingBallDetectorW21(Detector):
        name = "goalkeeper-and-moving-ball-stub-w21"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            x = 300 - self._call_count * 5
            self._call_count += 1
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("goalkeeper-and-moving-ball-stub-w21", _GoalkeeperAndMovingBallDetectorW21)

    monkeypatch.setenv("WORKER_DETECTOR", "goalkeeper-and-moving-ball-stub-w21")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "play_situation")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    situation = saved["play_situation_result"]
    assert situation is not None
    assert situation["ball_detected"] is True
    assert situation["goalkeeper_detected"] is True
    assert situation["situation"] in (
        "unknown", "ball_stationary", "ball_moving", "shot_detected",
    )
    assert situation["sub_state"] in (None, "shot_towards_goal", "shot_away_from_goal")
    assert saved["analysis_results"]["play_situation"] == situation
    assert saved["analysis_statistics"]["analyzers_run"] == ["play_situation"]


async def test_engine_with_goalkeeper_decision_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro se movendo lateralmente + bola se
    movendo em linha reta, ambos com o mesmo track_id do inicio ao fim).
    WORKER_ANALYZERS inclui APENAS "goalkeeper_decision" - prova que a
    composicao de CINCO Analyzers (W15/W17/W19/W20/W21 reunidas) funciona
    mesmo sem nenhum deles estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingGoalkeeperAndBallDetectorW22(Detector):
        name = "moving-goalkeeper-and-ball-stub-w22"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            gk_y = 10 + self._call_count * 8
            ball_x = 300 - self._call_count * 5
            self._call_count += 1
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=gk_y, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=ball_x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("moving-goalkeeper-and-ball-stub-w22", _MovingGoalkeeperAndBallDetectorW22)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-goalkeeper-and-ball-stub-w22")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_decision")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    decision_result = saved["goalkeeper_decision_result"]
    assert decision_result is not None
    assert decision_result["ball_detected"] is True
    assert decision_result["goalkeeper_detected"] is True
    assert decision_result["decision"] in (
        "unknown", "stay_on_line", "step_forward", "step_back",
        "shift_left", "shift_right", "prepare_dive", "dive_left",
        "dive_right", "recover_position",
    )
    assert decision_result["goalkeeper_position"] is not None
    assert saved["analysis_results"]["goalkeeper_decision"] == decision_result
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_decision"]


async def test_engine_with_goalkeeper_decision_evaluation_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro se movendo lateralmente + bola se
    movendo). WORKER_ANALYZERS inclui APENAS "goalkeeper_decision_evaluation"
    - prova que a composicao de SEIS Analyzers (W15/W17/W19/W20/W21/W22
    reunidas) funciona mesmo sem nenhum deles estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingGoalkeeperAndBallDetectorW23(Detector):
        name = "moving-goalkeeper-and-ball-stub-w23"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            gk_y = 10 + self._call_count * 8
            ball_x = 300 - self._call_count * 5
            self._call_count += 1
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=gk_y, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=ball_x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("moving-goalkeeper-and-ball-stub-w23", _MovingGoalkeeperAndBallDetectorW23)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-goalkeeper-and-ball-stub-w23")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_decision_evaluation")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    evaluation_result = saved["goalkeeper_decision_evaluation_result"]
    assert evaluation_result is not None
    assert evaluation_result["evaluation"] in (
        "unknown", "insufficient_information", "compatible", "partially_compatible", "incompatible",
    )
    assert isinstance(evaluation_result["rules_evaluated"], list)
    assert len(evaluation_result["rules_evaluated"]) == 6
    assert len(evaluation_result["explanations"]) == 6
    assert saved["analysis_results"]["goalkeeper_decision_evaluation"] == evaluation_result
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_decision_evaluation"]


async def test_engine_with_play_outcome_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro parado + bola se movendo). WORKER_ANALYZERS
    inclui APENAS "play_outcome" - prova que a composicao de CINCO
    Analyzers (W15/W17/W19/W20/W21/W22 reunidas) funciona mesmo sem
    nenhum deles estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingBallAndGoalkeeperDetectorW24(Detector):
        name = "moving-ball-and-goalkeeper-stub-w24"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            ball_x = 300 - self._call_count * 5
            self._call_count += 1
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=ball_x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("moving-ball-and-goalkeeper-stub-w24", _MovingBallAndGoalkeeperDetectorW24)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-ball-and-goalkeeper-stub-w24")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "play_outcome")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    outcome_result = saved["play_outcome_result"]
    assert outcome_result is not None
    assert outcome_result["outcome"] in (
        "unknown", "insufficient_information", "save", "goal", "ball_out",
        "blocked", "post", "crossbar", "lost_track", "no_shot_detected",
    )
    assert isinstance(outcome_result["supporting_evidence"], list)
    assert len(outcome_result["supporting_evidence"]) >= 1
    assert saved["analysis_results"]["play_outcome"] == outcome_result
    assert saved["analysis_statistics"]["analyzers_run"] == ["play_outcome"]


async def test_engine_with_goalkeeper_performance_evaluation_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro parado + bola se movendo). WORKER_ANALYZERS
    inclui APENAS "goalkeeper_performance_evaluation" - prova que a
    composicao de QUATRO Analyzers (W21/W22/W23/W24 reunidas) funciona
    mesmo sem nenhum deles estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingBallAndGoalkeeperDetectorW25(Detector):
        name = "moving-ball-and-goalkeeper-stub-w25"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            ball_x = 300 - self._call_count * 5
            self._call_count += 1
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=ball_x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("moving-ball-and-goalkeeper-stub-w25", _MovingBallAndGoalkeeperDetectorW25)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-ball-and-goalkeeper-stub-w25")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_performance_evaluation")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    performance_result = saved["goalkeeper_performance_evaluation_result"]
    assert performance_result is not None
    assert performance_result["performance"] in (
        "unknown", "insufficient_information", "excellent", "good", "adequate", "poor", "critical",
    )
    assert isinstance(performance_result["rules_evaluated"], list)
    assert len(performance_result["rules_evaluated"]) == 8
    assert "performance=" in performance_result["summary"]
    assert saved["analysis_results"]["goalkeeper_performance_evaluation"] == performance_result
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_performance_evaluation"]


async def test_engine_with_goalkeeper_coaching_analyzer_produces_a_coherent_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro parado + bola se movendo). WORKER_ANALYZERS
    inclui APENAS "goalkeeper_coaching" - prova que a composicao dos
    QUATRO Analyzers desta sprint (W22/W23/W24/W25 reunidas) funciona
    mesmo sem nenhum deles estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingBallAndGoalkeeperDetectorW26(Detector):
        name = "moving-ball-and-goalkeeper-stub-w26"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            ball_x = 300 - self._call_count * 5
            self._call_count += 1
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=ball_x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("moving-ball-and-goalkeeper-stub-w26", _MovingBallAndGoalkeeperDetectorW26)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-ball-and-goalkeeper-stub-w26")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_coaching")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    coaching_result = saved["goalkeeper_coaching_result"]
    assert coaching_result is not None
    assert coaching_result["coaching"] in (
        "unknown", "insufficient_information", "no_feedback", "keep_position", "improve_positioning",
        "move_earlier", "move_later", "attack_ball", "stay_patient", "recover_faster",
    )
    assert isinstance(coaching_result["rules_evaluated"], list)
    assert len(coaching_result["rules_evaluated"]) == 8
    assert "coaching=" in coaching_result["summary"]
    assert saved["analysis_results"]["goalkeeper_coaching"] == coaching_result
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_coaching"]


async def test_engine_with_goalkeeper_analysis_report_analyzer_produces_a_coherent_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integracao completa com Tracker/SceneAnalyzer/WorldModel/FootballDomain
    REAIS (sem mock) - mocka a inferencia do Detector para emitir DUAS
    deteccoes por frame (goleiro parado + bola se movendo). WORKER_ANALYZERS
    inclui APENAS "goalkeeper_analysis_report" - prova que o CONTRATO
    OFICIAL de saida do Worker (agregando os seis Analyzers cognitivos
    da W21-W26) funciona mesmo sem nenhum deles estar ativo na pipeline."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingBallAndGoalkeeperDetectorW27(Detector):
        name = "moving-ball-and-goalkeeper-stub-w27"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            self._call_count = 0

        def detect(self, frame) -> DetectionResult:
            ball_x = 300 - self._call_count * 5
            self._call_count += 1
            goalkeeper_detection = Detection(
                label=ClassLabel("goalkeeper"), confidence=Confidence(0.85),
                bbox=BoundingBox(x=10, y=10, width=20, height=40),
            )
            ball_detection = Detection(
                label=ClassLabel("sports ball"), confidence=Confidence(0.6),
                bbox=BoundingBox(x=ball_x, y=240, width=10, height=10),
            )
            return DetectionResult(detections=[goalkeeper_detection, ball_detection])

    register_detector("moving-ball-and-goalkeeper-stub-w27", _MovingBallAndGoalkeeperDetectorW27)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-ball-and-goalkeeper-stub-w27")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_WORLD_MODEL", "basic")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_analysis_report")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    report = saved["goalkeeper_analysis_report"]
    assert report is not None
    for key in (
        "play_situation", "goalkeeper_decision", "decision_evaluation", "play_outcome",
        "performance_evaluation", "coaching", "confidence_summary", "artifacts",
        "analysis_version", "worker_version", "generated_at",
    ):
        assert key in report
    assert set(report["artifacts"].keys()) == {
        "play_situation", "goalkeeper_decision", "goalkeeper_decision_evaluation",
        "play_outcome", "goalkeeper_performance_evaluation", "goalkeeper_coaching",
    }
    assert saved["analysis_results"]["goalkeeper_analysis_report"] == report
    assert saved["analysis_statistics"]["analyzers_run"] == ["goalkeeper_analysis_report"]


async def test_engine_produces_a_coherent_event_timeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sprint W28 (Perception Engine): integracao completa com
    Tracker/SceneAnalyzer REAIS (sem mock) - mocka so a inferencia do
    Detector (goleiro se movendo). Prova que "event_timeline" e uma chave
    NOVA no artefato (todas as chaves anteriores continuam existindo,
    inalteradas) e que ela contem fatos coerentes com o que
    detection_results/scene_events ja reportam separadamente."""
    from worker.inference.detectors.base import Detector
    from worker.inference.detectors.registry import register_detector
    from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult

    class _MovingGoalkeeperDetectorW28(Detector):
        name = "moving-goalkeeper-stub-w28"
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

    register_detector("moving-goalkeeper-stub-w28", _MovingGoalkeeperDetectorW28)

    monkeypatch.setenv("WORKER_DETECTOR", "moving-goalkeeper-stub-w28")
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence")
    get_settings.cache_clear()

    video = _make_video(tmp_path, frame_count=5)
    state = _make_state(tmp_path, video)

    result = await BasicVisionEngine(get_settings()).process(state)

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))

    # Nenhuma chave existente foi removida/alterada por esta sprint.
    assert saved["detection_results"] != []
    assert saved["scene_events"] != []
    assert saved["analysis_results"]["goalkeeper_presence"] is not None

    timeline = saved["event_timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) > 0

    event_types_seen = {event["event_type"] for event in timeline}
    assert "FrameProcessed" in event_types_seen
    assert "ObjectDetected" in event_types_seen
    assert "TrackStarted" in event_types_seen
    assert "AnalyzerStarted" in event_types_seen
    assert "AnalyzerFinished" in event_types_seen

    frame_processed_count = sum(1 for e in timeline if e["event_type"] == "FrameProcessed")
    assert frame_processed_count == 5

    # Todo evento tem event_id unico e parent_event_id ausente por padrao
    # (nenhum builder desta sprint tem uma cadeia causal alem de
    # RuleEvaluated -> AnalyzerFinished, e goalkeeper_presence nao produz
    # RuleEvaluated).
    event_ids = [event["event_id"] for event in timeline]
    assert len(event_ids) == len(set(event_ids))
    assert all(event["parent_event_id"] is None for event in timeline)

    # Ordenado por frame_index.
    frame_indexes = [event["frame_index"] for event in timeline]
    assert frame_indexes == sorted(frame_indexes)
