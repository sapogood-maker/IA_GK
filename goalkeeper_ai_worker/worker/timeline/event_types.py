"""Constantes de tipo de evento da Perception Timeline (Sprint W28).

Strings simples (nao Enum) para casar com o formato ja serializado em
`Event.to_dict()` e evitar uma camada extra de `.value` - mesmo padrao de
`PROCESSING_JOBS_STREAM` (app/core/queue.py/worker/infrastructure/redis/
consumer.py): uma constante nomeada em vez de magic string espalhada.

Subconjunto viavel nesta sprint - so tipos derivaveis dos dados que ja
existem em `ProcessorContext`, sem nenhuma inteligencia nova (ver
justificativa completa no plano da Sprint W28). `GoalkeeperCandidateDetected`/
`GoalDetected`/`SceneChanged` ficam para quando os Analyzers cognitivos
passarem a alimentar a Timeline (W33+) - registra-los agora exigiria
decidir heuristicas que pertencem aos Analyzers, nao a este registro de
fatos brutos.
"""
from __future__ import annotations

FRAME_PROCESSED = "FrameProcessed"

OBJECT_DETECTED = "ObjectDetected"
PERSON_DETECTED = "PersonDetected"
BALL_DETECTED = "BallDetected"

TRACK_STARTED = "TrackStarted"
TRACK_UPDATED = "TrackUpdated"
TRACK_LOST = "TrackLost"
TRACK_RECOVERED = "TrackRecovered"
OBJECT_ENTERED_REGION = "ObjectEnteredRegion"
OBJECT_LEFT_REGION = "ObjectLeftRegion"
OBJECT_STOPPED = "ObjectStopped"
OBJECT_MOVING = "ObjectMoving"
OCCLUSION_DETECTED = "OcclusionDetected"

ANALYZER_STARTED = "AnalyzerStarted"
ANALYZER_FINISHED = "AnalyzerFinished"
RULE_EVALUATED = "RuleEvaluated"

# Mapeia SceneEventType (worker/inference/events/types.py) -> constante
# unificada acima. Vive aqui (nao em builder.py) porque e parte do
# vocabulario de tipos, nao da logica de traducao.
FROM_SCENE_EVENT_TYPE = {
    "track_started": TRACK_STARTED,
    "track_updated": TRACK_UPDATED,
    "track_lost": TRACK_LOST,
    "track_recovered": TRACK_RECOVERED,
    "object_entered_frame": OBJECT_ENTERED_REGION,
    "object_left_frame": OBJECT_LEFT_REGION,
    "object_stopped": OBJECT_STOPPED,
    "object_moving": OBJECT_MOVING,
    "occlusion_detected": OCCLUSION_DETECTED,
}
