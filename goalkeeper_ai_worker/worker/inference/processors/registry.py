"""Registry de Processors — guarda quais classes de FrameProcessor estão
disponíveis, na ordem em que foram registradas.

A ordem de registro define a ordem de execução na pipeline (dicts do
Python preservam ordem de inserção) — adicionar um Processor novo (ex.:
`YOLOProcessor`, Sprint W8; `TrackingProcessor`, Sprint W9;
`SceneAnalysisProcessor`, Sprint W10) é só chamar `register_processor`
com ele; nenhuma mudança em `pipeline.py` é necessária. `YOLOProcessor` é
registrado antes de `TrackingProcessor` de propósito - o tracking associa
as detecções que o YOLO acabou de produzir no mesmo frame.
`SceneAnalysisProcessor` é registrado por último - interpreta o
TrackingResult que o tracking acabou de produzir no mesmo frame.
"""
from __future__ import annotations

from worker.inference.processors.base import FrameProcessor
from worker.inference.processors.color_processor import ColorProcessor
from worker.inference.processors.resize_processor import ResizeProcessor
from worker.inference.processors.roi_processor import ROIProcessor
from worker.inference.processors.scene_analysis_processor import SceneAnalysisProcessor
from worker.inference.processors.statistics_processor import StatisticsProcessor
from worker.inference.processors.tracking_processor import TrackingProcessor
from worker.inference.processors.yolo_processor import YOLOProcessor

_PROCESSORS: dict[str, type[FrameProcessor]] = {}


def register_processor(name: str, processor_class: type[FrameProcessor]) -> None:
    """Registra uma classe de Processor sob um nome."""
    _PROCESSORS[name] = processor_class


def get_processor_class(name: str) -> type[FrameProcessor] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _PROCESSORS.get(name)


def available_processors() -> list[str]:
    """Nomes de todos os Processors registrados, na ordem de registro
    (define a ordem de execução da pipeline)."""
    return list(_PROCESSORS)


register_processor("color", ColorProcessor)
register_processor("resize", ResizeProcessor)
register_processor("roi", ROIProcessor)
register_processor("statistics", StatisticsProcessor)
register_processor("yolo", YOLOProcessor)
register_processor("tracking", TrackingProcessor)
register_processor("scene_analysis", SceneAnalysisProcessor)
