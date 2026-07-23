"""Analyzer API - Sprint W13.

Primeira camada de ANÁLISE do domínio de futebol (`worker/domain/`,
Sprint W12, apenas MODELAVA o domínio - nenhuma decisão era tomada).
Todo Analyzer recebe exclusivamente um `FootballWorld`
(`worker.domain.football_world`) e devolve um `AnalysisResult` -
nunca conhece `WorldState`, `SceneAnalysisResult`, `TrackingResult`,
`DetectionResult`, OpenCV, YOLO, ByteTrack, Redis, Backend ou R2
(Boundary Enforcement, ver `base.py`).

Módulo irmão de `worker/domain/`, não um submódulo dele - `domain/`
modela o QUE existe (goleiro, bola, campo); `analyzers/` responde
PERGUNTAS sobre o que existe. `GoalkeeperPresenceAnalyzer` (primeira
implementação) responde só perguntas factuais e determinísticas -
nenhuma heurística, nenhuma regra de futebol, nenhum julgamento."""
