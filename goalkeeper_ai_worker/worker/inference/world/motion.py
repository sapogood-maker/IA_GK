"""compute_motion: apenas matemática - deslocamento, velocidade, direção,
aceleração. Nenhuma interpretação (não decide "parado"/"em movimento" -
isso é responsabilidade de `SceneAnalyzer`, uma camada abaixo).

Unidades: pixels e "por frame" (o World Model não recebe fps - só
frame_index - ver nota honesta em `world_state.py`/Constituição)."""
from __future__ import annotations

import math

from worker.inference.world.types import Motion, Position


def compute_motion(
    previous_position: Position | None,
    current_position: Position,
    previous_motion: Motion | None,
) -> Motion:
    """Calcula a cinemática entre a posição anterior e a atual.

    Sem posição anterior (primeira observação do objeto), devolve
    cinemática zerada - não há o que calcular ainda."""
    if previous_position is None:
        return Motion(displacement=0.0, speed=0.0, direction_degrees=0.0, acceleration=0.0)

    dx = current_position.x - previous_position.x
    dy = current_position.y - previous_position.y
    displacement = math.hypot(dx, dy)
    speed = displacement
    direction_degrees = math.degrees(math.atan2(dy, dx)) % 360.0
    previous_speed = previous_motion.speed if previous_motion is not None else 0.0
    acceleration = speed - previous_speed

    return Motion(
        displacement=displacement,
        speed=speed,
        direction_degrees=direction_degrees,
        acceleration=acceleration,
    )
