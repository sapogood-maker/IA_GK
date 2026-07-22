"""Ponto único de resolução do Detector ativo, a partir de configuração
(WORKER_DETECTOR) - nunca hardcoded em nenhum Processor.

Espelha `inference/engine.py` (create_engine) para a família de
Detectors."""
from __future__ import annotations

from worker.config.settings import WorkerSettings
from worker.inference.detectors.base import Detector
from worker.inference.detectors.exceptions import DetectorInitializationError
from worker.inference.detectors.registry import available_detectors, get_detector_class


def create_detector(detector_name: str, settings: WorkerSettings) -> Detector:
    """Instancia o Detector correspondente a `detector_name`.

    Levanta DetectorInitializationError se `detector_name` não estiver
    registrado, ou se a própria inicialização do Detector falhar (ex.:
    modelo/pesos ausentes) - nunca faz fallback silencioso para outro
    Detector."""
    detector_class = get_detector_class(detector_name)
    if detector_class is None:
        raise DetectorInitializationError(
            f"Detector desconhecido: '{detector_name}'. "
            f"Disponiveis: {', '.join(available_detectors())}"
        )
    try:
        return detector_class(settings)
    except DetectorInitializationError:
        raise
    except Exception as exc:
        raise DetectorInitializationError(
            f"Falha ao inicializar o Detector '{detector_name}': {exc}"
        ) from exc
