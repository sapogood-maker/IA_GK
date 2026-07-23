"""World Model API — abstração `WorldModel`, independente de qualquer
algoritmo de detecção/tracking/interpretação concreto (Sprint W11).

O World Model NÃO implementa regras de futebol. NÃO detecta objetos. NÃO
faz tracking. NÃO toma decisão alguma — ele apenas mantém um estado
consistente ("fotografia completa") do mundo observado, construído a
partir de `SceneAnalysisResult` (a saída de QUALQUER SceneAnalyzer, não
algo específico do `BasicSceneAnalyzer`).

Esta é a ÚLTIMA camada genérica da arquitetura de visão computacional.
A partir da Sprint W12, os primeiros analisadores específicos de futebol
(`GoalkeeperAnalyzer`, `BallAnalyzer`, `SaveAnalyzer`, `ShotAnalyzer`,
`DiveAnalyzer`, `GoalAnalyzer`) consumirão exclusivamente `WorldState` -
nenhum deles poderá depender diretamente de `Detector`, `Tracker`,
`SceneAnalyzer`, OpenCV, YOLO ou ByteTrack.

`WorldModel` conhece apenas `SceneAnalysisResult` (`worker.inference.
events.types`) - nunca `Detector`, `Tracker`, OpenCV, Redis, Backend ou
R2."""
