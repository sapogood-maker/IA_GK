"""API de Eventos de Cena — abstração `SceneAnalyzer`, independente de
qualquer algoritmo/biblioteca concreto (Sprint W10).

Recebe um `TrackingResult` (o contrato de saída de QUALQUER Tracker, não
algo específico do ByteTrack) e produz `SceneAnalysisResult` (uma lista de
`SceneEvent`s). Nenhuma regra de negócio de futebol aqui - nenhum evento
sabe o que é uma defesa, um gol, um chute, uma pose. Eventos genéricos de
cena (início/fim de trilha, movimento, oclusão) são a base sobre a qual
futuras análises específicas (`GoalkeeperAnalyzer`, `BallAnalyzer`,
`DiveAnalyzer`, `SaveAnalyzer`, `GoalAnalyzer`) serão construídas, sem
tocar em `PipelineProcessor`, `BasicVisionEngine`, `Detector` ou
`Tracker` - só consumindo `SceneEvent`s.

**Não confundir com `worker/events/`** (pacote de topo, Sprint W3) - lá
vivem os eventos de ciclo de vida do Job (`JobStarted`/`VideoDownloaded`/
etc., só logging). Este módulo (`worker/inference/events/`) é outra
família de conceito inteiramente distinta: eventos de interpretação de
cena, dentro da camada de inferência, gerados por Processor."""
