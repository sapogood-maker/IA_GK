"""TimelineExplorer: API de consulta sobre a Perception Timeline de um
artifact.json (Sprint W29).

Substitui os scripts descartaveis escritos ad-hoc para validar a W28
manualmente - esta e a ferramenta oficial e reutilizavel para qualquer
sprint futura inspecionar um artifact real: navegar por frame/tempo/
track_id/tipo de evento, reconstruir a sequencia cronologica, comparar a
Timeline com detection_results/tracking_results/analysis_results, e
exportar estatisticas.

Opera sobre o artifact INTEIRO (dict), nao so sobre `event_timeline`
isolado - e a unica forma de cumprir as comparacoes (esses campos sao
irmaos de `event_timeline` no mesmo payload). Nenhum metodo tem efeito
colateral sobre o artifact original; a unica escrita em disco
(`export_statistics`) sempre cria um arquivo NOVO.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from worker.timeline import event_types


class TimelineExplorer:
    """Consulta read-only sobre um artifact.json ja carregado."""

    def __init__(self, artifact: dict) -> None:
        self._artifact = artifact
        self._events: list[dict] = artifact.get("event_timeline", [])

    @classmethod
    def from_file(cls, path: str | Path) -> "TimelineExplorer":
        with open(path, encoding="utf-8") as f:
            artifact = json.load(f)
        return cls(artifact)

    # --- Navegacao ---

    def chronological(self) -> list[dict]:
        """Ordena por frame_index - garantia independente de o artifact ja
        vir ordenado (PerceptionTimeline.to_dict() ja ordena, mas o
        Explorer nao deveria depender disso silenciosamente)."""
        return sorted(self._events, key=lambda e: e["frame_index"])

    def by_frame(self, frame_index: int) -> list[dict]:
        return [e for e in self.chronological() if e["frame_index"] == frame_index]

    def by_time_range(self, start_seconds: float, end_seconds: float) -> list[dict]:
        return [
            e
            for e in self.chronological()
            if e["timestamp_seconds"] is not None and start_seconds <= e["timestamp_seconds"] <= end_seconds
        ]

    def by_frame_range(self, start_frame: int, end_frame: int) -> list[dict]:
        """Mesma familia de by_time_range, por indice de frame - usado
        pelo PlaySegmenter (Sprint W30) para nao precisar reimplementar
        filtragem de eventos por intervalo."""
        return [e for e in self.chronological() if start_frame <= e["frame_index"] <= end_frame]

    def by_track_id(self, track_id: int) -> list[dict]:
        return [e for e in self.chronological() if e["track_id"] == track_id]

    def by_event_type(self, event_type: str) -> list[dict]:
        return [e for e in self.chronological() if e["event_type"] == event_type]

    def reconstruct(self, up_to_frame: int | None = None) -> list[dict]:
        """Sequencia cronologica completa (ou so ate um frame de corte) -
        o "replay" que a Perception Timeline promete (Event Sourcing
        friendly, W28), exposto aqui como funcionalidade de verdade."""
        events = self.chronological()
        if up_to_frame is None:
            return events
        return [e for e in events if e["frame_index"] <= up_to_frame]

    # --- Explicacao legivel (formatacao de fatos existentes, nao inferencia nova) ---

    def explain(self, frame_index: int) -> list[str]:
        return [self._describe(event) for event in self.by_frame(frame_index)]

    @staticmethod
    def _describe(event: dict) -> str:
        timestamp = event["timestamp_seconds"]
        ts_text = f"t={timestamp:.2f}s" if timestamp is not None else "t=?"

        details = []
        if event.get("entity"):
            details.append(str(event["entity"]))
        if event.get("track_id") is not None:
            details.append(f"track_id={event['track_id']}")
        if event.get("confidence") is not None:
            details.append(f"conf={event['confidence']:.2f}")

        metadata = event.get("metadata") or {}
        if metadata.get("analyzer_name"):
            details.append(f"analyzer={metadata['analyzer_name']}")
        if metadata.get("rule_name"):
            outcome = "passou" if metadata.get("passed") else "falhou"
            details.append(f"rule={metadata['rule_name']} ({outcome})")

        # traco ASCII simples (nao em-dash) - o console do Windows nem
        # sempre renderiza unicode corretamente (achado durante a
        # validacao manual da W29)
        suffix = f" - {', '.join(details)}" if details else ""
        return f"frame {event['frame_index']} ({ts_text}): {event['event_type']}{suffix}"

    # --- Comparacao (cross-check Timeline x campos irmaos do artifact) ---

    def compare_with_detections(self) -> dict:
        """Conta, por frame, ObjectDetected na Timeline vs entradas em
        detection_results[frame]["detections"]. So o tipo generico
        ObjectDetected conta - BallDetected/PersonDetected sao eventos
        ADICIONAIS sobre a mesma deteccao (ver worker/timeline/builder.py),
        nao deteccoes extras."""
        detection_results = self._artifact.get("detection_results", [])
        expected_by_frame = {d["frame_index"]: len(d["detections"]) for d in detection_results}

        timeline_by_frame = Counter(
            e["frame_index"] for e in self._events if e["event_type"] == event_types.OBJECT_DETECTED
        )

        mismatches = []
        frames_matching = 0
        for frame_index, expected_count in expected_by_frame.items():
            actual_count = timeline_by_frame.get(frame_index, 0)
            if actual_count == expected_count:
                frames_matching += 1
            else:
                mismatches.append(
                    {
                        "frame_index": frame_index,
                        "timeline_count": actual_count,
                        "detection_results_count": expected_count,
                    }
                )

        return {
            "frames_checked": len(expected_by_frame),
            "frames_matching": frames_matching,
            "mismatches": mismatches,
            "consistent": not mismatches,
        }

    def compare_with_tracking(self) -> dict:
        """Compara scene_statistics.events_by_type (contagem cumulativa
        real, ja no artifact) com a contagem equivalente na Timeline, via
        o mesmo mapeamento usado pelo builder (event_types.FROM_SCENE_EVENT_TYPE)
        - reusa o vocabulario, nao duplica logica de traducao."""
        scene_statistics = self._artifact.get("scene_statistics") or {}
        events_by_type = scene_statistics.get("events_by_type", {})

        mismatches = []
        for scene_type, expected_count in events_by_type.items():
            unified_type = event_types.FROM_SCENE_EVENT_TYPE.get(scene_type, scene_type)
            actual_count = sum(1 for e in self._events if e["event_type"] == unified_type)
            if actual_count != expected_count:
                mismatches.append(
                    {
                        "event_type": unified_type,
                        "scene_statistics_count": expected_count,
                        "timeline_count": actual_count,
                    }
                )

        return {
            "types_checked": len(events_by_type),
            "mismatches": mismatches,
            "consistent": not mismatches,
        }

    def compare_with_analysis(self) -> dict:
        """analysis_results/analysis_statistics so guardam o ULTIMO frame
        por Analyzer (limitacao arquitetural ja documentada - ver
        PERCEPTION_ENGINE_ARCHITECTURE.md) - a comparacao nao pode ser
        frame-a-frame como as duas acima. Verifica consistencia
        estrutural: todo analyzer_name que rodou tem AnalyzerFinished na
        Timeline, nenhum sobra sem contrapartida, e para analyzers com
        Rule Evaluation, as regras do ULTIMO AnalyzerFinished (via
        parent_event_id) batem com rules_evaluated do resultado final."""
        analysis_statistics = self._artifact.get("analysis_statistics") or {}
        analyzers_run = set(analysis_statistics.get("analyzers_run", []))

        finished_events = [e for e in self._events if e["event_type"] == event_types.ANALYZER_FINISHED]
        analyzers_with_events = {e["metadata"]["analyzer_name"] for e in finished_events}

        missing_from_timeline = sorted(analyzers_run - analyzers_with_events)
        unexpected_in_timeline = sorted(analyzers_with_events - analyzers_run)

        analysis_results = self._artifact.get("analysis_results", {})
        rule_consistency: dict[str, dict] = {}
        for analyzer_name, result in analysis_results.items():
            expected_rules = result.get("rules_evaluated")
            if expected_rules is None:
                continue

            candidates = [e for e in finished_events if e["metadata"]["analyzer_name"] == analyzer_name]
            last_finished = max(candidates, key=lambda e: e["frame_index"], default=None)
            if last_finished is None:
                rule_consistency[analyzer_name] = {"consistent": False, "reason": "sem AnalyzerFinished na Timeline"}
                continue

            timeline_rules = sorted(
                e["metadata"]["rule_name"]
                for e in self._events
                if e["event_type"] == event_types.RULE_EVALUATED and e["parent_event_id"] == last_finished["event_id"]
            )
            rule_consistency[analyzer_name] = {
                "expected_rules": sorted(expected_rules),
                "timeline_rules": timeline_rules,
                "consistent": sorted(expected_rules) == timeline_rules,
            }

        return {
            "analyzers_run": sorted(analyzers_run),
            "analyzers_with_finished_events": sorted(analyzers_with_events),
            "missing_from_timeline": missing_from_timeline,
            "unexpected_in_timeline": unexpected_in_timeline,
            "rule_consistency": rule_consistency,
            "consistent": (
                not missing_from_timeline
                and not unexpected_in_timeline
                and all(v.get("consistent") for v in rule_consistency.values())
            ),
        }

    # --- Estatisticas ---

    def statistics(self) -> dict:
        by_event_type = Counter(e["event_type"] for e in self._events)
        by_track_id = Counter(e["track_id"] for e in self._events if e["track_id"] is not None)
        frame_indexes = [e["frame_index"] for e in self._events]
        timestamps = [e["timestamp_seconds"] for e in self._events if e["timestamp_seconds"] is not None]

        return {
            "total_events": len(self._events),
            "by_event_type": dict(by_event_type),
            "by_track_id": dict(by_track_id),
            "frame_range": [min(frame_indexes), max(frame_indexes)] if frame_indexes else None,
            "time_range_seconds": [min(timestamps), max(timestamps)] if timestamps else None,
            "distinct_frames_with_events": len(set(frame_indexes)),
        }

    def summary(self) -> dict:
        """Resumo executivo - frames/duracao, tracks, eventos, regras,
        analyzers. Usado pelo `--summary` do CLI (worker/explorers/cli.py)."""
        frame_metadata = self._artifact.get("frame_metadata") or {}
        tracking_statistics = self._artifact.get("tracking_statistics") or {}
        analysis_statistics = self._artifact.get("analysis_statistics") or {}
        stats = self.statistics()

        rule_events = [e for e in self._events if e["event_type"] == event_types.RULE_EVALUATED]
        rules_passed = sum(1 for e in rule_events if e["metadata"].get("passed"))

        return {
            "frame_count": frame_metadata.get("frame_count"),
            "duration_seconds": frame_metadata.get("duration_seconds"),
            "fps": frame_metadata.get("fps"),
            "total_tracks": tracking_statistics.get("total_tracks"),
            "total_events": stats["total_events"],
            "events_by_type": stats["by_event_type"],
            "rules_evaluated": len(rule_events),
            "rules_passed": rules_passed,
            "rules_failed": len(rule_events) - rules_passed,
            "analyzers_run": analysis_statistics.get("analyzers_run", []),
        }

    def export_statistics(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.statistics(), f, ensure_ascii=False, indent=2)
