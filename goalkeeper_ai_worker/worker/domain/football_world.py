"""FootballWorld: a representação do domínio de futebol num dado frame -
goleiro(s), bola(s), jogadores, balizas, campo. Nenhuma decisão é tomada
aqui - só estrutura.

Este é o único tipo que os analisadores futuros de futebol
(`GoalkeeperAnalyzer`, `BallAnalyzer`, `SaveAnalyzer`, `ShotAnalyzer`,
`DiveAnalyzer`, `GoalAnalyzer`, Sprint W13+) poderão consumir - nenhum
deles conhecerá `WorldState`/`SceneAnalyzer`/`Tracker`/`Detector`
diretamente (Seção 16 da Constituição)."""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

from worker.domain.entities.ball import Ball
from worker.domain.entities.field import Field
from worker.domain.entities.goal import Goal
from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.entities.player import Player


@dataclass
class FootballWorld:
    """Fotografia do domínio de futebol num dado frame."""

    frame_index: int = 0
    goalkeepers: list[Goalkeeper] = dataclass_field(default_factory=list)
    players: list[Player] = dataclass_field(default_factory=list)
    balls: list[Ball] = dataclass_field(default_factory=list)
    goals: list[Goal] = dataclass_field(default_factory=list)
    field: Field = dataclass_field(default_factory=Field.default)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "goalkeepers": [gk.to_dict() for gk in self.goalkeepers],
            "players": [player.to_dict() for player in self.players],
            "balls": [ball.to_dict() for ball in self.balls],
            "goals": [goal.to_dict() for goal in self.goals],
            "field": self.field.to_dict(),
        }
