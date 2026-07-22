"""Testes de worker.config.settings."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.core.exceptions import ConfigurationError


def test_settings_load_from_environment() -> None:
    """Os valores definidos via variaveis de ambiente devem ser carregados corretamente."""
    settings = get_settings()
    assert settings.instance_id == "worker-test-01"
    assert settings.env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.backend_api_url == "http://backend.test"
    assert settings.api_key == "test-api-key"


def test_settings_defaults_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    """Campos opcionais devem assumir seus valores padrao quando nao definidos."""
    monkeypatch.delenv("WORKER_ENV", raising=False)
    monkeypatch.delenv("WORKER_LOG_LEVEL", raising=False)
    monkeypatch.delenv("WORKER_REDIS_URL", raising=False)
    monkeypatch.delenv("WORKER_CONSUMER_GROUP", raising=False)
    monkeypatch.delenv("WORKER_LOCK_TTL_SECONDS", raising=False)
    monkeypatch.delenv("WORKER_PROTOCOL_VERSION", raising=False)
    monkeypatch.delenv("WORKER_INFERENCE_ENGINE", raising=False)
    monkeypatch.delenv("WORKER_FRAME_SKIP", raising=False)
    monkeypatch.delenv("WORKER_ENABLE_RESIZE", raising=False)
    monkeypatch.delenv("WORKER_ENABLE_ROI", raising=False)
    monkeypatch.delenv("WORKER_ENABLE_COLOR_PROCESSOR", raising=False)
    monkeypatch.delenv("WORKER_ENABLE_STATISTICS_PROCESSOR", raising=False)
    monkeypatch.delenv("WORKER_DETECTOR", raising=False)
    monkeypatch.delenv("WORKER_MODEL_PATH", raising=False)
    monkeypatch.delenv("WORKER_CONFIDENCE_THRESHOLD", raising=False)
    monkeypatch.delenv("WORKER_IOU_THRESHOLD", raising=False)
    monkeypatch.delenv("WORKER_TRACKER", raising=False)
    monkeypatch.delenv("WORKER_TRACKING_ENABLED", raising=False)
    monkeypatch.delenv("WORKER_TRACK_MIN_CONFIDENCE", raising=False)
    monkeypatch.delenv("WORKER_TRACK_MAX_AGE", raising=False)
    monkeypatch.delenv("WORKER_TRACK_MIN_HITS", raising=False)
    monkeypatch.delenv("WORKER_SCENE_ANALYZER", raising=False)
    monkeypatch.delenv("WORKER_SCENE_ANALYSIS_ENABLED", raising=False)
    monkeypatch.delenv("WORKER_SCENE_MOTION_THRESHOLD_PX", raising=False)
    monkeypatch.delenv("WORKER_SCENE_OCCLUSION_IOU_THRESHOLD", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.env == "development"
    assert settings.log_level == "INFO"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.consumer_group == "goalkeeper_ai_worker"
    assert settings.lock_ttl_seconds == 300
    assert settings.protocol_version == "1.0"
    assert settings.inference_engine == "basic_vision"
    assert settings.frame_skip == 0
    assert settings.enable_resize is False
    assert settings.enable_roi is False
    assert settings.target_width == 0
    assert settings.target_height == 0
    assert settings.roi_x == 0
    assert settings.roi_y == 0
    assert settings.roi_width == 0
    assert settings.roi_height == 0
    assert settings.enable_color_processor is True
    assert settings.enable_statistics_processor is True
    assert settings.detector == ""
    assert settings.model_path == "weights/yolo11n.pt"
    assert settings.confidence_threshold == 0.25
    assert settings.iou_threshold == 0.45
    assert settings.tracker == ""
    assert settings.tracking_enabled is False
    assert settings.track_min_confidence == 0.25
    assert settings.track_max_age == 30
    assert settings.track_min_hits == 1
    assert settings.scene_analyzer == ""
    assert settings.scene_analysis_enabled is False
    assert settings.scene_motion_threshold_px == 5.0
    assert settings.scene_occlusion_iou_threshold == 0.3


def test_settings_scene_analysis_options_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_SCENE_ANALYZER/WORKER_SCENE_ANALYSIS_ENABLED/
    WORKER_SCENE_MOTION_THRESHOLD_PX/WORKER_SCENE_OCCLUSION_IOU_THRESHOLD
    devem ser lidos do ambiente, permitindo trocar de SceneAnalyzer (ou
    seus parametros) sem mudar codigo."""
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "basic")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("WORKER_SCENE_MOTION_THRESHOLD_PX", "10")
    monkeypatch.setenv("WORKER_SCENE_OCCLUSION_IOU_THRESHOLD", "0.5")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.scene_analyzer == "basic"
    assert settings.scene_analysis_enabled is True
    assert settings.scene_motion_threshold_px == 10
    assert settings.scene_occlusion_iou_threshold == 0.5


def test_settings_tracker_options_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_TRACKER/WORKER_TRACKING_ENABLED/WORKER_TRACK_MIN_CONFIDENCE/
    WORKER_TRACK_MAX_AGE/WORKER_TRACK_MIN_HITS devem ser lidos do
    ambiente, permitindo trocar de Tracker (ou seus parametros) sem mudar
    codigo."""
    monkeypatch.setenv("WORKER_TRACKER", "bytetrack")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    monkeypatch.setenv("WORKER_TRACK_MIN_CONFIDENCE", "0.4")
    monkeypatch.setenv("WORKER_TRACK_MAX_AGE", "15")
    monkeypatch.setenv("WORKER_TRACK_MIN_HITS", "3")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.tracker == "bytetrack"
    assert settings.tracking_enabled is True
    assert settings.track_min_confidence == 0.4
    assert settings.track_max_age == 15
    assert settings.track_min_hits == 3


def test_settings_detector_options_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_DETECTOR/WORKER_MODEL_PATH/WORKER_CONFIDENCE_THRESHOLD/
    WORKER_IOU_THRESHOLD devem ser lidos do ambiente, permitindo trocar de
    Detector (ou seus parametros) sem mudar codigo."""
    monkeypatch.setenv("WORKER_DETECTOR", "yolo")
    monkeypatch.setenv("WORKER_MODEL_PATH", "weights/custom.pt")
    monkeypatch.setenv("WORKER_CONFIDENCE_THRESHOLD", "0.5")
    monkeypatch.setenv("WORKER_IOU_THRESHOLD", "0.6")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.detector == "yolo"
    assert settings.model_path == "weights/custom.pt"
    assert settings.confidence_threshold == 0.5
    assert settings.iou_threshold == 0.6


def test_settings_processor_toggles_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_ENABLE_COLOR_PROCESSOR/WORKER_ENABLE_STATISTICS_PROCESSOR devem
    ser lidos do ambiente, permitindo desabilitar Processors sem mudar codigo."""
    monkeypatch.setenv("WORKER_ENABLE_COLOR_PROCESSOR", "false")
    monkeypatch.setenv("WORKER_ENABLE_STATISTICS_PROCESSOR", "false")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.enable_color_processor is False
    assert settings.enable_statistics_processor is False


def test_settings_vision_engine_options_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_FRAME_SKIP/ENABLE_RESIZE/TARGET_*/ENABLE_ROI/ROI_* devem ser lidos do ambiente."""
    monkeypatch.setenv("WORKER_FRAME_SKIP", "2")
    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "true")
    monkeypatch.setenv("WORKER_TARGET_WIDTH", "320")
    monkeypatch.setenv("WORKER_TARGET_HEIGHT", "240")
    monkeypatch.setenv("WORKER_ENABLE_ROI", "true")
    monkeypatch.setenv("WORKER_ROI_X", "10")
    monkeypatch.setenv("WORKER_ROI_Y", "20")
    monkeypatch.setenv("WORKER_ROI_WIDTH", "100")
    monkeypatch.setenv("WORKER_ROI_HEIGHT", "80")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.frame_skip == 2
    assert settings.enable_resize is True
    assert settings.target_width == 320
    assert settings.target_height == 240
    assert settings.enable_roi is True
    assert settings.roi_x == 10
    assert settings.roi_y == 20
    assert settings.roi_width == 100
    assert settings.roi_height == 80


def test_settings_inference_engine_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_INFERENCE_ENGINE deve ser lido do ambiente, sem exigir mudanca de codigo."""
    monkeypatch.setenv("WORKER_INFERENCE_ENGINE", "opencv")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.inference_engine == "opencv"


def test_missing_instance_id_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_INSTANCE_ID e obrigatorio - sua ausencia deve falhar de forma clara."""
    monkeypatch.delenv("WORKER_INSTANCE_ID", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()


def test_missing_backend_api_url_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_BACKEND_API_URL e obrigatorio - sua ausencia deve falhar de forma clara."""
    monkeypatch.delenv("WORKER_BACKEND_API_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()


def test_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKER_API_KEY e obrigatorio - sua ausencia deve falhar de forma clara."""
    monkeypatch.delenv("WORKER_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()
