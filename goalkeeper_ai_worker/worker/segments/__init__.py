"""Play Segmentation (Sprint W30) - agrupa milhares de Events da
Perception Timeline (W28) em segmentos de jogada (`PlaySegment`), via uma
`SegmentStrategy` plugavel (mesma disciplina de Registry/Factory ja usada
por Detector/Tracker/SceneAnalyzer/WorldModel/Analyzer).

`PlaySegment` e puramente estrutural - nenhum julgamento sobre o que a
jogada "significa" (isso continua exclusivo dos Analyzers, camada acima,
nao tocada por esta sprint). Nao integrado a BasicVisionEngine/
artifact.json ainda - invocado sob demanda (CLI da W29, testes, sprints
futuras). Ver PERCEPTION_ENGINE_ARCHITECTURE.md, Sprint W30.
"""
