"""Testes de worker.inference.processors.registry."""
from __future__ import annotations

from worker.analyzers.processor import AnalyzerProcessor
from worker.config.settings import get_settings
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.inference.processors.color_processor import ColorProcessor
from worker.inference.processors.registry import (
    _PROCESSORS,
    available_processors,
    get_processor_class,
    register_processor,
)
from worker.inference.processors.resize_processor import ResizeProcessor
from worker.inference.processors.roi_processor import ROIProcessor
from worker.inference.processors.football_domain_processor import FootballDomainProcessor
from worker.inference.processors.scene_analysis_processor import SceneAnalysisProcessor
from worker.inference.processors.statistics_processor import StatisticsProcessor
from worker.inference.processors.tracking_processor import TrackingProcessor
from worker.inference.processors.world_model_processor import WorldModelProcessor
from worker.inference.processors.yolo_processor import YOLOProcessor
from worker.video.metadata import FrameMetadata


def test_all_ten_default_processors_are_registered() -> None:
    assert get_processor_class("color") is ColorProcessor
    assert get_processor_class("resize") is ResizeProcessor
    assert get_processor_class("roi") is ROIProcessor
    assert get_processor_class("statistics") is StatisticsProcessor
    assert get_processor_class("yolo") is YOLOProcessor
    assert get_processor_class("tracking") is TrackingProcessor
    assert get_processor_class("scene_analysis") is SceneAnalysisProcessor
    assert get_processor_class("world_model") is WorldModelProcessor
    assert get_processor_class("football_domain") is FootballDomainProcessor
    assert get_processor_class("analyzer") is AnalyzerProcessor


def test_registration_order_defines_pipeline_order() -> None:
    assert available_processors() == [
        "color", "resize", "roi", "statistics", "yolo", "tracking",
        "scene_analysis", "world_model", "football_domain", "analyzer",
    ]


def test_get_processor_class_returns_none_for_unknown_name() -> None:
    assert get_processor_class("nao-existe") is None


class _DummyProcessor(FrameProcessor):
    """Processor de teste - prova que registrar um Processor novo e
    suficiente para incluí-lo na pipeline, sem alterar pipeline.py."""

    name = "dummy"

    def __init__(self, settings) -> None:
        pass

    @classmethod
    def is_enabled(cls, settings) -> bool:
        return True

    def process(self, frame, metadata: FrameMetadata, context: ProcessorContext):
        context.record(self.name, 0.0)
        return frame, metadata, context


def test_registering_a_new_processor_appends_it_to_available_processors() -> None:
    try:
        register_processor("dummy-test-processor", _DummyProcessor)

        assert "dummy-test-processor" in available_processors()
        assert get_processor_class("dummy-test-processor") is _DummyProcessor
    finally:
        # Evita vazar o Processor de teste para outros testes que iteram
        # available_processors() (ex.: PipelineProcessor.from_settings()).
        _PROCESSORS.pop("dummy-test-processor", None)
