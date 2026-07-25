"""Timeline Explorer CLI (Sprint W29).

Substitui os scripts descartaveis escritos ad-hoc para validar a Perception
Timeline manualmente (Sprint W28) - ferramenta oficial e reutilizavel para
inspecionar um artifact.json real: navegar por frame/tempo/track_id/tipo
de evento, reconstruir a sequencia cronologica, comparar a Timeline com
detection_results/tracking_results/analysis_results, exportar estatisticas
e obter um resumo executivo. Mesmo padrao de uso de
worker/healthcheck.py/worker/wait_for_redis.py (main()->int, docstring de
uso no topo) - primeiro script do Worker com argumentos (argparse).

Uso: python -m worker.explorers.cli ARTIFACT_PATH [opcoes]
"""
from __future__ import annotations

import argparse
import json
import sys

from worker.explorers.timeline_explorer import TimelineExplorer
from worker.segments.factory import create_strategy
from worker.segments.play_segment import PlaySegment
from worker.segments.segmenter import PlaySegmenter


def _print_events(events: list[dict]) -> None:
    for event in events:
        print(json.dumps(event, ensure_ascii=False))


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _describe_segment(segment: PlaySegment) -> str:
    """Geracao de texto humano do PlaySegment vive aqui (CLI), nunca em
    PlaySegment/TimelineExplorer (Sprint W30 - evita acoplar W29 a W30)."""
    duration = segment.duration_seconds if segment.duration_seconds is not None else 0.0
    ball_text = "presente" if segment.ball_involved else "ausente"
    return (
        f"Segmento {segment.segment_id[:8]} - frames {segment.start_frame}-{segment.end_frame} "
        f"({duration:.1f}s): {len(segment.track_ids)} track(s), {len(segment.events)} eventos, "
        f"bola {ball_text}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m worker.explorers.cli",
        description="Timeline Explorer - observabilidade da Perception Timeline.",
    )
    parser.add_argument("artifact_path", help="Caminho para um artifact.json")

    navigation = parser.add_argument_group("navegacao")
    navigation.add_argument("--frame", type=int, metavar="N", help="Eventos de um frame especifico")
    navigation.add_argument(
        "--time-range", type=float, nargs=2, metavar=("START", "END"), help="Eventos entre dois timestamps (segundos)"
    )
    navigation.add_argument("--track-id", type=int, metavar="ID", help="Eventos de um track_id especifico")
    navigation.add_argument("--event-type", metavar="TYPE", help="Eventos de um tipo especifico (ex.: TrackStarted)")
    navigation.add_argument("--chronological", action="store_true", help="Toda a Timeline, em ordem cronologica")
    navigation.add_argument("--limit", type=int, metavar="N", help="Limita a quantidade impressa (com --chronological)")
    navigation.add_argument("--explain", type=int, metavar="FRAME", help="Explicacao legivel dos eventos de um frame")

    comparison = parser.add_argument_group("comparacao")
    comparison.add_argument("--compare-detections", action="store_true")
    comparison.add_argument("--compare-tracking", action="store_true")
    comparison.add_argument("--compare-analysis", action="store_true")

    reporting = parser.add_argument_group("relatorios")
    reporting.add_argument("--stats", action="store_true", help="Estatisticas da Timeline")
    reporting.add_argument("--export", metavar="PATH", help="Grava --stats como JSON neste caminho")
    reporting.add_argument("--summary", action="store_true", help="Resumo executivo do artifact")

    segmentation = parser.add_argument_group("segmentacao (Sprint W30)")
    segmentation.add_argument(
        "--segments", action="store_true", help="Segmenta a Timeline em jogadas (GapStrategy)"
    )
    segmentation.add_argument(
        "--max-gap", type=float, default=1.0, metavar="SECONDS",
        help="Gap maximo, em segundos, para a GapStrategy (default: 1.0)",
    )

    return parser


def run(args: argparse.Namespace) -> int:
    explorer = TimelineExplorer.from_file(args.artifact_path)
    ran_something = False

    if args.frame is not None:
        _print_events(explorer.by_frame(args.frame))
        ran_something = True
    if args.time_range is not None:
        start, end = args.time_range
        _print_events(explorer.by_time_range(start, end))
        ran_something = True
    if args.track_id is not None:
        _print_events(explorer.by_track_id(args.track_id))
        ran_something = True
    if args.event_type is not None:
        _print_events(explorer.by_event_type(args.event_type))
        ran_something = True
    if args.chronological:
        events = explorer.chronological()
        if args.limit is not None:
            events = events[: args.limit]
        _print_events(events)
        ran_something = True
    if args.explain is not None:
        for line in explorer.explain(args.explain):
            print(line)
        ran_something = True
    if args.compare_detections:
        _print_json(explorer.compare_with_detections())
        ran_something = True
    if args.compare_tracking:
        _print_json(explorer.compare_with_tracking())
        ran_something = True
    if args.compare_analysis:
        _print_json(explorer.compare_with_analysis())
        ran_something = True
    if args.stats:
        _print_json(explorer.statistics())
        if args.export:
            explorer.export_statistics(args.export)
        ran_something = True
    if args.summary:
        _print_json(explorer.summary())
        ran_something = True
    if args.segments:
        strategy = create_strategy("gap", max_gap_seconds=args.max_gap)
        segments = PlaySegmenter(strategy).segment(explorer)
        for segment in segments:
            print(_describe_segment(segment))
        ran_something = True

    if not ran_something:
        print("Nenhuma opcao informada - use --help para ver os comandos disponiveis.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
