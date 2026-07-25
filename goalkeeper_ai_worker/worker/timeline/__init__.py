"""Perception Timeline (Sprint W28) - fundacao temporal do Goalkeeper AI.

Registra fatos de percepcao (deteccoes, tracking, eventos de cena,
execucao de Analyzers) como uma sequencia imutavel de `Event`s, em vez de
um snapshot que so guarda o ultimo frame. Nao substitui nenhuma camada
existente (Detector/Tracker/SceneAnalyzer/WorldModel/FootballDomain/
Analyzer) - e derivada delas, apos o loop de frames terminar (ver
`builder.build_timeline`). Ver PERCEPTION_ENGINE_ARCHITECTURE.md, Sprint
W28.

Distinto de `worker.events.events` (ciclo de vida do Job - JobStarted/
JobCompleted/etc.) - dois conceitos diferentes que so compartilham a
palavra "evento" (ver nota em worker/events/events.py).
"""
