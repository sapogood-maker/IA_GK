"""Registry de Trackers - guarda quais classes de Tracker estão
disponíveis, por nome.

Especialização do Plugin Registry (AI_WORKER_CONSTITUTION.md, Seção 6)
para a família de Trackers - paralela ao Registry de motores, de
Processors e de Detectors, cada um independente. Adicionar um Tracker
novo (BoT-SORT, DeepSORT, StrongSORT, OC-SORT): escrever uma classe que
implementa `Tracker` (base.py) e chamar `register_tracker` com ela -
nenhuma mudança em `TrackingProcessor`, `factory.py` ou no restante do
Worker."""
from __future__ import annotations

from worker.inference.trackers.base import Tracker
from worker.inference.trackers.bytetrack_tracker import ByteTrackTracker

_TRACKERS: dict[str, type[Tracker]] = {}


def register_tracker(name: str, tracker_class: type[Tracker]) -> None:
    """Registra uma classe de Tracker sob um nome."""
    _TRACKERS[name] = tracker_class


def get_tracker_class(name: str) -> type[Tracker] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _TRACKERS.get(name)


def available_trackers() -> list[str]:
    """Nomes de todos os Trackers registrados no momento."""
    return sorted(_TRACKERS)


register_tracker("bytetrack", ByteTrackTracker)
