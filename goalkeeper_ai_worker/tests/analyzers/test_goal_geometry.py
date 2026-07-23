"""Testes de worker.analyzers.goal_geometry.GoalGeometryAnalyzer -
implementacao real (sem mock), totalmente deterministica: nenhuma
avaliacao de goleiro, defesa, chute, mergulho ou reacao."""
from __future__ import annotations

from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.results import GoalGeometryResult
from worker.analyzers.types import GoalZone
from worker.config.settings import get_settings
from worker.domain.entities.goal import Goal
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.region import Region


def _goal(x: float = 0, y: float = 0, width: float = 90, height: float = 30) -> Goal:
    return Goal(region=Region(x=x, y=y, width=width, height=height))


def test_no_goal_present() -> None:
    analyzer = GoalGeometryAnalyzer(get_settings())
    world = FootballWorld(frame_index=5, goals=[])

    result = analyzer.analyze(world)

    assert isinstance(result, GoalGeometryResult)
    assert result.frame_index == 5
    assert result.goal_detected is False
    assert result.goal_center is None
    assert result.goal_width is None
    assert result.goal_height is None
    assert result.left_post is None
    assert result.right_post is None
    assert result.goal_regions is None
    assert result.confidence is None


def test_well_formed_goal_produces_full_geometry() -> None:
    analyzer = GoalGeometryAnalyzer(get_settings())
    world = FootballWorld(frame_index=10, goals=[_goal(x=0, y=0, width=90, height=30)])

    result = analyzer.analyze(world)

    assert result.goal_detected is True
    assert result.goal_width == 90
    assert result.goal_height == 30
    assert result.goal_center.x == 45
    assert result.goal_center.y == 15
    assert result.left_post.x == 0 and result.left_post.y == 0
    assert result.right_post.x == 90 and result.right_post.y == 0
    assert result.confidence == 1.0


def test_goal_regions_form_a_2x3_grid_covering_the_whole_goal() -> None:
    analyzer = GoalGeometryAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, goals=[_goal(x=0, y=0, width=90, height=30)])

    result = analyzer.analyze(world)

    assert set(result.goal_regions.keys()) == {
        GoalZone.TOP_LEFT, GoalZone.TOP_CENTER, GoalZone.TOP_RIGHT,
        GoalZone.BOTTOM_LEFT, GoalZone.BOTTOM_CENTER, GoalZone.BOTTOM_RIGHT,
    }
    top_left = result.goal_regions[GoalZone.TOP_LEFT]
    assert (top_left.x, top_left.y, top_left.width, top_left.height) == (0, 0, 30, 15)
    bottom_right = result.goal_regions[GoalZone.BOTTOM_RIGHT]
    assert (bottom_right.x, bottom_right.y, bottom_right.width, bottom_right.height) == (60, 15, 30, 15)


def test_degenerate_goal_region_has_zero_confidence_and_no_regions() -> None:
    analyzer = GoalGeometryAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, goals=[_goal(x=0, y=0, width=0, height=30)])

    result = analyzer.analyze(world)

    assert result.goal_detected is True
    assert result.confidence == 0.0
    assert result.goal_regions is None


def test_multiple_goals_selects_the_first_deterministically() -> None:
    analyzer = GoalGeometryAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0,
        goals=[_goal(x=0, y=0, width=90, height=30), _goal(x=500, y=0, width=90, height=30)],
    )

    result = analyzer.analyze(world)

    assert result.goal_center.x == 45  # o primeiro gol, sempre


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalGeometryAnalyzer(get_settings())
    result = analyzer.analyze(FootballWorld(frame_index=0))

    assert result.metadata.analyzer_name == "goal_geometry"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
