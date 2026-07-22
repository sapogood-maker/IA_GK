"""Registry de Detectors - guarda quais classes de Detector estão
disponíveis, por nome.

Especialização do Plugin Registry (AI_WORKER_CONSTITUTION.md, Seção 6)
para a família de Detectors - paralela ao Registry de motores
(`inference/registry.py`) e ao de Processors (`inference/processors/
registry.py`), cada um independente. Adicionar um Detector novo (ex.:
RT-DETR, GroundingDINO, OWLv2): escrever uma classe que implementa
`Detector` (base.py) e chamar `register_detector` com ela - nenhuma
mudança em `YOLOProcessor`, `factory.py` ou no restante do Worker."""
from __future__ import annotations

from worker.inference.detectors.base import Detector
from worker.inference.detectors.yolo_detector import YOLODetector

_DETECTORS: dict[str, type[Detector]] = {}


def register_detector(name: str, detector_class: type[Detector]) -> None:
    """Registra uma classe de Detector sob um nome."""
    _DETECTORS[name] = detector_class


def get_detector_class(name: str) -> type[Detector] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _DETECTORS.get(name)


def available_detectors() -> list[str]:
    """Nomes de todos os Detectors registrados no momento."""
    return sorted(_DETECTORS)


register_detector("yolo", YOLODetector)
