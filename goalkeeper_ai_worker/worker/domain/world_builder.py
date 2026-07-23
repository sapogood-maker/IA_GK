"""FootballWorldBuilder: transforma um WorldState (genérico, Seção 6.1)
num FootballWorld (domínio de futebol). Apenas transforma dados - nenhuma
heurística, nenhuma decisão, nenhuma interpretação.

**Como cada entidade é classificada (a única "decisão" desta sprint, e
não é uma heurística comportamental):** o rótulo (`ObjectState.label`) já
atribuído pelo Detector é comparado contra três conjuntos fixos de
rótulos conhecidos (goleiro/bola/jogador) - um despacho por tipo,
puramente estrutural, não uma inferência sobre o COMPORTAMENTO do
objeto. Com o modelo padrão hoje (YOLO11n, treinado em COCO), o único
rótulo de pessoa que existe é `"person"` - por isso, na prática, todo
mundo aparece como `Player` e `goalkeepers`/`FootballWorld.goalkeepers`
fica vazio até que um modelo treinado especificamente para este domínio
(com uma classe `"goalkeeper"` própria) seja usado."""
from __future__ import annotations

from worker.config.settings import WorkerSettings
from worker.domain.context import FootballDomainContext
from worker.domain.entities.ball import Ball
from worker.domain.entities.field import Field
from worker.domain.entities.goal import Goal
from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.entities.player import Player
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId, TrackedFootballEntity
from worker.inference.world.object_state import ObjectState
from worker.inference.world.world_state import WorldState

_GOALKEEPER_LABELS = frozenset({"goalkeeper", "keeper"})
_BALL_LABELS = frozenset({"ball", "sports ball", "futsal ball", "frisbee"})
_PLAYER_LABELS = frozenset({"player", "person"})


class FootballWorldBuilder:
    """Única responsabilidade: transformar WorldState em FootballWorld -
    nenhuma regra de negócio, nenhuma decisão além de despacho por rótulo."""

    def __init__(self, settings: WorkerSettings) -> None:
        """Construído com `settings` (mesma convenção uniforme já usada
        por todo Engine/Processor/Detector/Tracker/SceneAnalyzer/
        WorldModel) - não usa nenhum campo de configuração hoje, mas
        mantém a assinatura uniforme."""
        self._context = FootballDomainContext()

    def build(self, world_state: WorldState) -> FootballWorld:
        goalkeepers: list[Goalkeeper] = []
        players: list[Player] = []
        balls: list[Ball] = []

        for obj in world_state.active_objects:
            entity = self._build_entity(obj)
            if isinstance(entity, Goalkeeper):
                goalkeepers.append(entity)
            elif isinstance(entity, Ball):
                balls.append(entity)
            elif isinstance(entity, Player):
                players.append(entity)
            # Rotulo desconhecido: ignorado silenciosamente - nao e um
            # objeto do dominio de futebol reconhecido por esta sprint.

        if self._context.field is None:
            self._context.field = Field.default()
            self._context.goals = Goal.default_pair(self._context.field.region)

        return FootballWorld(
            frame_index=world_state.frame_index,
            goalkeepers=goalkeepers,
            players=players,
            balls=balls,
            goals=list(self._context.goals),
            field=self._context.field,
        )

    def _build_entity(self, obj: ObjectState) -> TrackedFootballEntity | None:
        label = obj.label.lower()
        if label in _GOALKEEPER_LABELS:
            entity_class = Goalkeeper
        elif label in _BALL_LABELS:
            entity_class = Ball
        elif label in _PLAYER_LABELS:
            entity_class = Player
        else:
            return None

        previous_position = None
        if obj.previous_bbox is not None:
            previous_position = Coordinate(
                x=obj.previous_bbox.x + obj.previous_bbox.width / 2,
                y=obj.previous_bbox.y + obj.previous_bbox.height / 2,
            )
        velocity = Vector.from_polar(obj.motion.speed, obj.motion.direction_degrees)
        bbox = Region(x=obj.bbox.x, y=obj.bbox.y, width=obj.bbox.width, height=obj.bbox.height)

        return entity_class(
            track_id=EntityId(obj.track_id),
            label=ClassLabel(obj.label),
            confidence=Confidence(obj.confidence),
            position=Coordinate(x=obj.position.x, y=obj.position.y),
            previous_position=previous_position,
            velocity=velocity,
            speed=obj.motion.speed,
            bbox=bbox,
            age=obj.age,
            frames_visible=obj.frames_visible,
            frames_hidden=obj.frames_hidden,
            active=obj.active,
        )

    def reset(self) -> None:
        """Limpa Field/Goal memorizados. Chamado uma vez no início de
        cada Job - aplica a lição da W9 (estado entre Jobs, Seção 6.1)
        proativamente, sem precisar redescobri-la nesta sprint."""
        self._context.reset()
