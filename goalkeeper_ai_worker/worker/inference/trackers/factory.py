"""Ponto único de resolução do Tracker ativo, a partir de configuração
(WORKER_TRACKER) - nunca hardcoded em nenhum Processor.

Espelha `inference/detectors/factory.py` (create_detector) para a família
de Trackers."""
from __future__ import annotations

from worker.config.settings import WorkerSettings
from worker.inference.trackers.base import Tracker
from worker.inference.trackers.exceptions import TrackerInitializationError
from worker.inference.trackers.registry import available_trackers, get_tracker_class


def create_tracker(tracker_name: str, settings: WorkerSettings) -> Tracker:
    """Instancia o Tracker correspondente a `tracker_name`.

    Levanta TrackerInitializationError se `tracker_name` não estiver
    registrado, ou se a própria inicialização do Tracker falhar - nunca
    faz fallback silencioso para outro Tracker."""
    tracker_class = get_tracker_class(tracker_name)
    if tracker_class is None:
        raise TrackerInitializationError(
            f"Tracker desconhecido: '{tracker_name}'. "
            f"Disponiveis: {', '.join(available_trackers())}"
        )
    try:
        return tracker_class(settings)
    except TrackerInitializationError:
        raise
    except Exception as exc:
        raise TrackerInitializationError(
            f"Falha ao inicializar o Tracker '{tracker_name}': {exc}"
        ) from exc
