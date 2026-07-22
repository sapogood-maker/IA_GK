# SPRINT_W10_REPORT.md — Goalkeeper AI Worker: Scene Events API

> Escopo: introduzir a primeira camada de interpretação de cena, isolada atrás de uma abstração própria (`SceneAnalyzer`) — genérica, sem nenhuma lógica específica de futebol (defesa/gol/chute/pose/MediaPipe/classificação, todos explicitamente fora de escopo). **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W9_REPORT.md` antes de implementar.

- **`worker/inference/events/base.py`** (novo) — `SceneAnalyzer` (ABC): contrato único `analyze(tracking_result: TrackingResult) -> SceneAnalysisResult` + `reset()` (concreto, default no-op). `SceneAnalyzer` conhece o contrato `TrackingResult` (a saída de QUALQUER Tracker) — não conhece ByteTrack/YOLO especificamente, mesma lógica já usada para justificar `Tracker` conhecer `DetectionResult` (W9).
- **`worker/inference/events/types.py`** (novo) — `SceneEventType` (enum com os 9 tipos pedidos: `track_started`/`track_updated`/`track_lost`/`track_recovered`/`object_entered_frame`/`object_left_frame`/`object_stopped`/`object_moving`/`occlusion_detected`), `MotionState` (`unknown`/`moving`/`stopped`), `TrackLifecycle` (`new`/`active`/`lost`), `SceneEvent` (event_type/track_id/frame_index/label/motion_state/lifecycle/related_track_id + `to_dict()`), `SceneStatistics` (cumulativas — mesmo padrão de `TrackingStatistics`), `SceneAnalysisResult` (+ `to_dict()`).
- **`worker/inference/events/context.py`** (novo) — `SceneAnalysisContext`/`TrackObservation`: memória interna PRIVADA de uma instância de `SceneAnalyzer` entre chamadas (última bbox/estado/movimento conhecidos por `track_id`) — não é o `ProcessorContext` do pipeline.
- **`worker/inference/events/exceptions.py`** (novo) — `SceneAnalysisError` → `SceneAnalysisInitializationError`/`SceneAnalysisExecutionError`, ambas de `WorkerError`.
- **`worker/inference/events/registry.py`** (novo) — `register_analyzer`/`get_analyzer_class`/`available_analyzers()`. Registry independente do de motores, Processors, Detectors e Trackers — cinco Registries paralelos.
- **`worker/inference/events/factory.py`** (novo) — `create_analyzer(nome, settings)`, espelhando `trackers/factory.py`.
- **`worker/inference/events/scene_analyzer.py`** (novo) — `BasicSceneAnalyzer(SceneAnalyzer)`: primeira implementação real. Deriva eventos comparando o `TrackingResult` do frame atual contra a memória de `SceneAnalysisContext` — ver "Lógica de emissão de eventos" abaixo.
- **`worker/inference/processors/scene_analysis_processor.py`** (novo) — `SceneAnalysisProcessor(FrameProcessor)`: **não detecta, rastreia nem transforma a imagem, só interpreta**: lê `context.tracking_results[-1]` (o `TrackingResult` que `TrackingProcessor` acabou de produzir no MESMO frame), chama `SceneAnalyzer.analyze()`, acumula o resultado no contexto. No-op seguro se `context.tracking_results` estiver vazio. `is_enabled` reflete `settings.scene_analysis_enabled and bool(settings.scene_analyzer)`. `reset()` delega a `self._analyzer.reset()`.
- **`worker/inference/processors/base.py`** (estendido) — `ProcessorContext` ganhou `scene_analysis_results: list[SceneAnalysisResult]` + `add_scene_analysis_result`/`scene_events_to_dict()` (este último achata os eventos de TODOS os frames numa lista cronológica única).
- **`worker/inference/processors/registry.py`** — `SceneAnalysisProcessor` registrado por último (`color → resize → roi → statistics → yolo → tracking → scene_analysis`).
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"scene_events"`, `"scene_statistics"`, `"scene_processing_time_ms"`.
- **`worker/config/settings.py`** — 4 campos novos: `scene_analyzer` (default `""`), `scene_analysis_enabled` (default `False`), `scene_motion_threshold_px` (default `5.0`), `scene_occlusion_iou_threshold` (default `0.3`).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `InferenceEngine.process`, `FrameProcessor.process`, `Detector.detect`, `Tracker.track` são idênticos aos de antes; `PipelineState`, `Pipeline`, `Orchestrator`, `Redis`, `BackendClient`, `Storage`, `video/`, `Detector`, `Tracker`, `YOLOProcessor`, `TrackingProcessor` não mudaram uma linha.

## Lógica de emissão de eventos (`BasicSceneAnalyzer`)

Para cada `TrackedObject` do frame atual, comparado contra a última observação conhecida (`SceneAnalysisContext.observations[track_id]`):

| Situação | Evento(s) emitido(s) |
|---|---|
| `track_id` nunca visto antes | `TRACK_STARTED` + `OBJECT_ENTERED_FRAME` |
| `track_id` estava `LOST`, reaparece | `TRACK_RECOVERED` |
| `track_id` ativo, deslocamento do centro da bbox < `WORKER_SCENE_MOTION_THRESHOLD_PX` (transição MOVING→STOPPED) | `OBJECT_STOPPED` |
| `track_id` ativo, deslocamento ≥ limiar (transição STOPPED→MOVING) | `OBJECT_MOVING` |
| `track_id` ativo, sem transição de movimento | `TRACK_UPDATED` |
| `track_id` estava ativo, ausente do frame atual | `TRACK_LOST` + `OBJECT_LEFT_FRAME` |
| Duas trilhas do MESMO frame com IoU ≥ `WORKER_SCENE_OCCLUSION_IOU_THRESHOLD` | `OCCLUSION_DETECTED` (par a par) |

**Nota de design documentada honestamente** (também no código e na Constituição, Risco 18): como `analyze()` recebe só um `TrackingResult` (sem dimensões do frame), `OBJECT_ENTERED_FRAME`/`OBJECT_LEFT_FRAME` são emitidos exatamente no mesmo momento que `TRACK_STARTED`/`TRACK_LOST` — a única informação disponível sobre "visibilidade" é a própria presença/ausência no `TrackingResult`, não a posição geométrica real em relação às bordas do frame.

`SceneStatistics` é **cumulativa** (mesmo padrão de `TrackingStatistics`, W9): `total_events`/`events_by_type` acumulam desde o último `reset()`, não só o frame atual.

## Testes — 176/176 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Tipos | `test_types.py` (events) | `SceneEvent.to_dict()`/`SceneAnalysisResult.to_dict()` serializam corretamente |
| Registry | `test_registry.py` (events) | `BasicSceneAnalyzer` registrado; nome desconhecido devolve `None`; registrar um analisador novo o disponibiliza |
| Factory | `test_factory.py` (events) | Nome desconhecido levanta `SceneAnalysisInitializationError`; falha de `__init__` é envolvida na mesma exceção; resolve `basic` |
| `BasicSceneAnalyzer` (real, sem mock) | `test_scene_analyzer.py` | Todos os 9 tipos de evento exercitados individualmente com `TrackingResult`s sintéticos: primeira aparição, continuidade, transições de movimento (stopped→moving e vice-versa), perda/recuperação de trilha, oclusão (com e sem sobreposição real), estatísticas cumulativas corretas, `reset()` limpa observações |
| `SceneAnalysisProcessor` (mocka só o SceneAnalyzer) | `test_scene_analysis_processor.py` | `is_enabled` exige os dois interruptores; no-op quando não há tracking no frame; analisa o último `TrackingResult` e registra no contexto; `reset()` delega ao analisador |
| Integração completa — cena real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_scene_analysis_enabled_produces_coherent_scene_events` | Mocka só o Detector (objeto se movendo), Tracker e SceneAnalyzer REAIS produzem `scene_events` coerentes: `track_started` uma única vez, `track_id` estável, estatísticas batendo com a contagem real de eventos |
| Reset entre Jobs (real, sem mock) | `test_basic_vision_engine.py::test_engine_resets_scene_analyzer_state_between_jobs` | A mesma instância de `BasicVisionEngine` processa 2 vídeos em sequência; `track_started` aparece nos DOIS vídeos (não só no primeiro) |
| Configuração | `test_settings.py` | `test_settings_scene_analysis_options_are_configurable` + extensão de `test_settings_defaults_apply` |
| Regressão | Todos os 151 testes anteriores (W1-W9) | Sem alteração de comportamento não intencional |

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/ tests/` → só a mesma menção em docstring de sempre, nenhum `import` real cruzado.
- `grep -rln "ByteTrack\|ultralytics\|bytetrack" worker/inference/events/*.py` (excluindo `.pyc`) → só docstrings explicando que `SceneAnalyzer` NÃO conhece ByteTrack. Nenhum `import` real de `ultralytics`/`bytetrack_tracker.py`.
- `grep -rn "yolo\|YOLO" worker/inference/events/` → nenhuma ocorrência.
- `PipelineProcessor`/`BasicVisionEngine` continuam importando só módulos internos do Worker + `numpy` — nenhuma biblioteca externa de IA/tracking/interpretação.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/sessão da W7/W8/W9. Gerei um vídeo real de 20 frames (640×480, 5fps) com um círculo vermelho se movendo, parando por 6 frames, e voltando a se mover — especificamente desenhado para exercitar `OBJECT_STOPPED`/`OBJECT_MOVING`, não só `TRACK_STARTED`/`TRACK_UPDATED`. Upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack` + `WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic` + `WORKER_SCENE_ANALYSIS_ENABLED=true`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`). YOLO11n classificou honestamente o círculo como `"frisbee"` (mesmo comportamento honesto da W9) — o que importa para a W10 é a coerência dos `scene_events`:

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis']
scene_statistics: {'total_tracks_observed': 1, 'active_tracks': 1, 'lost_tracks': 0,
                    'total_events': 21,
                    'events_by_type': {'track_started': 1, 'object_entered_frame': 1,
                                       'track_updated': 17, 'object_stopped': 1, 'object_moving': 1}}

frame  0  track_started         track_id=1
frame  0  object_entered_frame  track_id=1
frame  1-8  track_updated       track_id=1  motion=moving      (bola se movendo)
frame  9  object_stopped        track_id=1  motion=stopped     (bola acabou de parar)
frame 10-13  track_updated      track_id=1  motion=stopped     (bola parada)
frame 14  object_moving         track_id=1  motion=moving      (bola voltou a se mover)
frame 15-19  track_updated      track_id=1  motion=moving
```

**Confirmado exatamente o que a sprint pediu:** `SceneEvents` coerentes — `TRACK_STARTED`/`OBJECT_ENTERED_FRAME` uma única vez no frame 0, `TrackId` estável (1) do início ao fim, transições de movimento detectadas nos frames corretos (9 e 14, batendo com a posição real do círculo no vídeo gerado), estatísticas cumulativas corretas (21 eventos = soma exata de `events_by_type`). `scene_processing_time_ms` mediu `0.0` — computação puramente aritmética sobre 1-2 objetos, abaixo da resolução do timer nesta plataforma (mesmo comportamento já observado em `ColorProcessor`/`StatisticsProcessor` em sprints anteriores, não um bug). Lock liberado, mensagem confirmada (`XPENDING` = 0). Stack derrubado ao final.

## Riscos (novos, registrados na Constituição - Seção 14)

18. **`OBJECT_ENTERED_FRAME`/`OBJECT_LEFT_FRAME` são sinônimos exatos de `TRACK_STARTED`/`TRACK_LOST`** nesta implementação — consequência direta de `analyze()` não receber dimensões do frame. Documentado honestamente; corrigir exigiria estender o contrato de entrada.
19. **`SceneStatistics`/`TrackingStatistics` cumulativas dependem inteiramente do `reset()` rodar antes de cada Job** — se uma falha entre Jobs pular esse reset, as estatísticas do próximo vídeo inflariam silenciosamente (herda a mesma superfície de risco do Risco 17, agora com uma segunda instância stateful).

## Correção de curso documentada

A revisão W4.1 previa um futuro "Event Registry técnico" como submódulo de `worker/events/` (o pacote de eventos de ciclo de vida do Job, Sprint W3). Na prática, a API de Eventos de Cena foi implementada em `worker/inference/events/` — mais perto da camada de inferência que a consome, e um nome de pasta que colide (mas não conflita, por estarem em níveis diferentes da árvore) com `worker/events/`. `AI_WORKER_CONSTITUTION.md` foi atualizada para deixar essa distinção explícita em ambos os locais (Seção 1, linhas `events/events.py` e `inference`).

## Preparação para a W11

A W11 ainda não tem escopo definido (qual análise específica de futebol entra primeiro — `GoalkeeperAnalyzer`/`BallAnalyzer`/`DiveAnalyzer`/`SaveAnalyzer`/`GoalAnalyzer`). O que já está confirmado, pela repetição do mesmo padrão em W8/W9/W10: uma nova camada de análise que consome `SceneEvent`s exige apenas um novo Processor + (se necessário) uma nova família de Registry/`factory.py` — nunca uma mudança em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `VideoReader`, Redis, Backend, R2, ou nas famílias de Plugin já existentes (`Detector`/`Tracker`/`SceneAnalyzer` permanecem intocados). Diferença real da W11: pela primeira vez a lógica introduzida terá semântica de domínio (regras de futebol), não conceitos genéricos de visão computacional.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
