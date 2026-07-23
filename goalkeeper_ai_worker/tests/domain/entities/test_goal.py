"""Testes de worker.domain.entities.goal.Goal."""
from __future__ import annotations

from worker.domain.entities.goal import Goal
from worker.domain.geometry.region import Region


def test_default_pair_produces_two_goals_at_opposite_ends() -> None:
    field_region = Region(x=0.0, y=0.0, width=1.0, height=1.0)

    goals = Goal.default_pair(field_region)

    assert len(goals) == 2
    left_goal, right_goal = goals
    assert left_goal.region.x == 0.0
    assert right_goal.region.x > left_goal.region.x
    assert right_goal.region.x + right_goal.region.width == field_region.width


def test_goal_to_dict() -> None:
    goal = Goal(region=Region(x=0, y=1, width=2, height=3))
    assert goal.to_dict() == {"region": {"x": 0, "y": 1, "width": 2, "height": 3}}
