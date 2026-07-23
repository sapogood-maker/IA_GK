"""Football Domain Model — a primeira camada específica do domínio de
futebol (Sprint W12). Transforma `WorldState` (genérico, `worker.
inference.world`) em `FootballWorld` (goleiro(s), bola(s), jogadores,
balizas, campo).

**Esta sprint NÃO implementa análise, IA ou regras de negócio.** Ela só
cria os conceitos fundamentais do domínio - nenhuma decisão é tomada,
nenhuma interpretação é realizada, nenhuma heurística existe. A
classificação de rótulo em `world_builder.py` (goleiro/bola/jogador) é
despacho estrutural, não inferência comportamental.

`worker/domain/` é deliberadamente um pacote de topo, IRMÃO de
`worker/inference/`, não um submódulo dele - marca a fronteira real
entre "infraestrutura de visão computacional genérica" (inference/) e
"modelagem do domínio de futebol" (domain/). O Football Domain Model
conhece apenas `WorldState` (`worker.inference.world.world_state`) -
nunca `Detector`, `Tracker`, `SceneAnalyzer`, OpenCV, YOLO, ByteTrack,
Redis, Backend ou R2.

A partir da Sprint W13, os primeiros analisadores específicos de futebol
(`GoalkeeperAnalyzer`, `BallAnalyzer`, `SaveAnalyzer`, `ShotAnalyzer`,
`DiveAnalyzer`, `GoalAnalyzer`) consumirão exclusivamente `FootballWorld`
- nenhum deles conhecerá `WorldState` diretamente."""
