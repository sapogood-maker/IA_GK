"""Testes de worker.analyzers.goalkeeper_presence.GoalkeeperPresenceAnalyzer
- implementacao real (sem mock), totalmente deterministica: nenhuma
heuristica, nenhuma regra de futebol, nenhuma avaliacao."""
from __future__ import annotations

from worker.analyzers.goalkeeper_presence import GoalkeeperPresenceAnalyzer
from worker.analyzers.results import GoalkeeperPresenceResult
from worker.config.settings import get_settings
from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId


def _goalkeeper(track_id: int = 1, active: bool = True, age: int = 5) -> Goalkeeper:
    return Goalkeeper(
        track_id=EntityId(track_id), label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
        position=Coordinate(x=100, y=200), previous_position=Coordinate(x=95, y=200),
        velocity=Vector(dx=5, dy=0), speed=5.0, bbox=Region(x=90, y=180, width=20, height=40),
        age=age, frames_visible=age, frames_hidden=0, active=active,
    )


def test_no_goalkeeper_present() -> None:
    analyzer = GoalkeeperPresenceAnalyzer(get_settings())
    world = FootballWorld(frame_index=3, goalkeepers=[])

    result = analyzer.analyze(world)

    assert isinstance(result, GoalkeeperPresenceResult)
    assert result.frame_index == 3
    assert result.exists is False
    assert result.visible is False
    assert result.goalkeeper_count == 0
    assert result.track_id is None
    assert result.age is None
    assert result.current_position is None
    assert result.current_bbox is None


def test_single_goalkeeper_present_and_visible() -> None:
    analyzer = GoalkeeperPresenceAnalyzer(get_settings())
    world = FootballWorld(frame_index=10, goalkeepers=[_goalkeeper(track_id=7, active=True, age=15)])

    result = analyzer.analyze(world)

    assert result.exists is True
    assert result.visible is True
    assert result.goalkeeper_count == 1
    assert result.track_id == 7
    assert result.age == 15
    assert result.current_position == Coordinate(x=100, y=200)
    assert result.current_bbox == Region(x=90, y=180, width=20, height=40)


def test_goalkeeper_present_but_not_visible() -> None:
    analyzer = GoalkeeperPresenceAnalyzer(get_settings())
    world = FootballWorld(frame_index=1, goalkeepers=[_goalkeeper(active=False)])

    result = analyzer.analyze(world)

    assert result.exists is True
    assert result.visible is False


def test_multiple_goalkeepers_selects_the_first_deterministically() -> None:
    analyzer = GoalkeeperPresenceAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=1,
        goalkeepers=[_goalkeeper(track_id=1), _goalkeeper(track_id=2)],
    )

    result = analyzer.analyze(world)

    assert result.goalkeeper_count == 2
    assert result.track_id == 1  # o primeiro da lista, sempre


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperPresenceAnalyzer(get_settings())
    result = analyzer.analyze(FootballWorld(frame_index=0))

    assert result.metadata.analyzer_name == "goalkeeper_presence"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
