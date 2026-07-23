"""Testes de worker.inference.world.trajectory.Trajectory - historico
limitado de posicoes, composicao sobre History (nunca duplica logica de
buffer limitado)."""
from __future__ import annotations

from worker.inference.world.trajectory import Trajectory
from worker.inference.world.types import Position


def test_trajectory_accumulates_points_up_to_max_length() -> None:
    trajectory = Trajectory(max_length=3)

    for x in (1, 2, 3):
        trajectory.add_point(Position(x=x, y=0))

    assert trajectory.points == [Position(x=1, y=0), Position(x=2, y=0), Position(x=3, y=0)]
    assert len(trajectory) == 3


def test_trajectory_never_grows_beyond_max_length() -> None:
    trajectory = Trajectory(max_length=2)

    for x in (1, 2, 3, 4):
        trajectory.add_point(Position(x=x, y=0))

    assert trajectory.points == [Position(x=3, y=0), Position(x=4, y=0)]
    assert len(trajectory) == 2
