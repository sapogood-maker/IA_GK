# SPRINT_W11_REPORT.md — Goalkeeper AI Worker: World Model API

> Escopo: construir a última camada genérica da arquitetura de visão computacional — o World Model, que mantém um estado consistente ("fotografia completa") do mundo observado. Não implementa regra de futebol, não detecta, não rastreia, não interpreta cena, não toma decisão — apenas memória. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W10_REPORT.md` antes de implementar.

- **`worker/inference/world/base.py`** (novo) — `WorldModel` (ABC): contrato único `update(scene_result: SceneAnalysisResult) -> WorldState` + `reset()` (concreto, default no-op). `WorldModel` conhece apenas `SceneAnalysisResult` — nunca `Detector`, `Tracker`, OpenCV, YOLO, ByteTrack, Redis, Backend ou R2.
- **`worker/inference/world/types.py`** (novo) — `ObjectId`/`ClassLabel`/`Confidence` (`NewType`), `BoundingBox`, `Position`, `Motion` (displacement/speed/direction_degrees/acceleration — apenas matemática, nenhuma interpretação). Deliberadamente independentes de `trackers/types.py`/`detectors/types.py` — `world/` nunca importa de lá, só de `events/types.py`.
- **`worker/inference/world/history.py`** (novo) — `History[T]`: buffer circular genérico (`deque(maxlen=N)`), reutilizado por `Trajectory` e pelo próprio `WorldModel` (eventos recentes) — uma única implementação de "nunca cresce infinitamente".
- **`worker/inference/world/trajectory.py`** (novo) — `Trajectory`: histórico limitado de posições de um objeto, composição sobre `History`.
- **`worker/inference/world/motion.py`** (novo) — `compute_motion()`: função pura, calcula deslocamento/velocidade/direção/aceleração entre duas posições.
- **`worker/inference/world/object_state.py`** (novo) — `ObjectState`: estado completo de um objeto (track_id/label/confidence/bbox/previous_bbox/position/motion/trajectory/age/frames_visible/frames_hidden/active/first_seen_frame/last_seen_frame + `time_in_scene_frames`). Zero lógica de goleiro.
- **`worker/inference/world/world_state.py`** (novo) — `WorldStatistics` (reflete o estado ATUAL, não cumulativo), `WorldState` (a fotografia completa — active/lost/new_objects + recent_events + statistics).
- **`worker/inference/world/context.py`** (novo) — `WorldModelContext`: memória interna mutável (`ObjectState` mais recente por `track_id`), análoga a `SceneAnalysisContext` (W10).
- **`worker/inference/world/exceptions.py`** (novo) — `WorldModelError` → `WorldModelInitializationError`/`WorldModelExecutionError`.
- **`worker/inference/world/registry.py`**/**`factory.py`** (novos) — `register_world_model`/`get_world_model_class`/`available_world_models()`, `create_world_model(nome, settings)`. Sexto Registry paralelo (motores, Processors, Detectors, Trackers, SceneAnalyzers, WorldModels).
- **`worker/inference/world/world_model.py`** (novo) — `BasicWorldModel(WorldModel)`: primeira implementação real.
- **`worker/inference/processors/world_model_processor.py`** (novo) — `WorldModelProcessor(FrameProcessor)`: lê `context.scene_analysis_results[-1]`, chama `WorldModel.update()`, acumula o `WorldState`. No-op se não houver análise de cena no frame. `is_enabled` reflete `settings.world_model_enabled and bool(settings.world_model)`. `reset()` delega ao WorldModel.
- **`worker/inference/processors/base.py`** — `ProcessorContext` ganhou `world_states: list[WorldState]` + `add_world_state()`.
- **`worker/inference/processors/registry.py`** — `WorldModelProcessor` registrado por último (`color → resize → roi → statistics → yolo → tracking → scene_analysis → world_model`).
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"world_state"` (singular — o ÚLTIMO, uma fotografia), `"world_statistics"`, `"object_count"`, `"active_tracks"`, `"lost_tracks"`, `"average_speed"`, `"processing_time_ms"`.
- **`worker/config/settings.py`** — 5 campos novos: `world_model` (default `""`), `world_model_enabled` (default `False`), `world_history_size` (default `30`), `world_max_trajectory` (default `30`), `world_max_objects` (default `200`).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** (além da extensão aditiva de `SceneAnalysisResult`, ver abaixo) — `InferenceEngine.process`, `FrameProcessor.process`, `Detector.detect`, `Tracker.track`, `SceneAnalyzer.analyze` são idênticos aos de antes.

## Achado arquitetural necessário: `SceneObjectSnapshot`

Antes de implementar `BasicWorldModel.update()`, precisei verificar se `SceneAnalysisResult` (W10) já carregava dados suficientes para construir `ObjectState` (posição, bbox). **Não carregava**: `SceneEvent` descreve só TRANSIÇÕES (`track_started`, `object_stopped`, etc.), nunca bbox/confidence — essa informação nunca precisou sair de `TrackingResult` até agora.

Como a regra desta sprint é explícita ("O World Model conhece apenas SceneAnalysisResult" — nunca `TrackingResult` diretamente), a única correção arquiteturalmente honesta era estender `SceneAnalysisResult` com um canal posicional. Adicionei `SceneObjectSnapshot` (track_id/label/confidence/bbox) a `events/types.py` e um novo campo `SceneAnalysisResult.objects: list[SceneObjectSnapshot]` (default `[]` — extensão aditiva, não quebra nenhum teste/contrato da W10). `BasicSceneAnalyzer.analyze()` ganhou uma linha para populá-lo a partir do `TrackingResult` que ele já recebia. Validado que os 21 testes da W10 continuam passando após a extensão, mais 2 testes novos confirmando que `objects` é populado corretamente.

## World Model

```python
class WorldModel(ABC):
    name: str
    version: str
    def __init__(self, settings: WorkerSettings) -> None: ...
    def update(self, scene_result: SceneAnalysisResult) -> WorldState: ...
    def reset(self) -> None: ...  # concreto, default no-op
```

`create_world_model(nome, settings)` resolve o WorldModel ativo a partir de `WORKER_WORLD_MODEL`, espelhando `create_analyzer`. Trocar `BasicWorldModel` por uma implementação alternativa: escrever uma nova classe, registrá-la, apontar `WORKER_WORLD_MODEL=x` — sem tocar em `WorldModelProcessor`, `PipelineProcessor`, `BasicVisionEngine`, `Detector`, `Tracker`, `SceneAnalyzer` ou qualquer outro módulo.

## World State

`WorldState` é a fotografia completa: `active_objects`/`lost_objects`/`new_objects` (listas de `ObjectState`), `recent_events` (janela limitada de `SceneEvent`s, `WORKER_WORLD_HISTORY_SIZE`), `statistics` (`WorldStatistics` — reflete o estado ATUAL, não cumulativo como `TrackingStatistics`/`SceneStatistics`, já que uma fotografia não é um log).

**Princípio de implementação central:** `BasicWorldModel` nunca muta um `ObjectState` existente — cada `update()` constrói instâncias NOVAS e substitui a entrada em `WorldModelContext`. Isso garante que um `WorldState` já devolvido continue sendo fiel àquele instante mesmo que o WorldModel siga avançando internamente (evita o "vazamento de mutabilidade" que aconteceria se `active_objects` compartilhasse referências vivas com o próximo frame).

## Object State

Cada objeto tem: `track_id`/`label`/`confidence`/`bbox`/`previous_bbox`/`position`/`motion`/`trajectory` (lista de `Position`, já achatada da `Trajectory` viva)/`age`/`frames_visible`/`frames_hidden`/`active`/`first_seen_frame`/`last_seen_frame` + `time_in_scene_frames` (propriedade calculada). **Nenhuma lógica específica de goleiro.**

**Nota honesta:** `time_in_scene_frames` é expresso em número de FRAMES, não segundos — o World Model nunca recebe `fps` (só `frame_index`), mesma limitação já documentada para `OBJECT_ENTERED_FRAME`/`OBJECT_LEFT_FRAME` na W10 (Risco 18, agora Risco 20).

## Trajetória

`Trajectory` (composição sobre `History`) — histórico limitado de posições, "últimos N pontos", `N` configurável via `WORKER_WORLD_MAX_TRAJECTORY`, nunca cresce além disso (`deque(maxlen=N)`).

## Histórico

`History[T]` — buffer circular genérico, reutilizado por `Trajectory` (posições de um objeto) e pelo próprio `WorldModel` (`recent_events` — janela de `SceneEvent`s recentes, `WORKER_WORLD_HISTORY_SIZE`). Uma única implementação de "buffer limitado" evita duplicar a lógica de descarte em dois lugares.

## WorldModelProcessor

```
frame → WorldModelProcessor.process()
    → context.scene_analysis_results vazio? → no-op
    → latest = context.scene_analysis_results[-1]   [SceneAnalysisResult do MESMO frame]
    → self._world_model.update(latest)
    → WorldState
    → context.add_world_state(world_state)
    → devolve (frame, metadata, context) inalterados - so mantem estado, nunca detecta/rastreia/interpreta/transforma
```

Registrado por último na pipeline (`color → resize → roi → statistics → yolo → tracking → scene_analysis → world_model`).

## Configuração

| Variável | Default | Efeito |
|---|---|---|
| `WORKER_WORLD_MODEL` | `""` (vazio) | Nome do WorldModel ativo. Vazio = `WorldModelProcessor` desabilitado. |
| `WORKER_WORLD_MODEL_ENABLED` | `false` | Interruptor mestre — precisa estar `true` **e** `WORKER_WORLD_MODEL` precisa apontar para um WorldModel válido. |
| `WORKER_WORLD_HISTORY_SIZE` | `30` | Quantos `SceneEvent`s recentes `WorldState.recent_events` mantém. |
| `WORKER_WORLD_MAX_TRAJECTORY` | `30` | Quantos pontos `ObjectState.trajectory` mantém. |
| `WORKER_WORLD_MAX_OBJECTS` | `200` | Total máximo de objetos (ativos+perdidos) retidos; ao exceder, remove os LOST mais antigos primeiro. `<=0` desativa. |

## Testes — 219/219 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Tipos | `test_types.py` (world) | `Motion.to_dict()` |
| History | `test_history.py` | Mantém até `max_size`; descarta o mais antigo além disso; `reset()` |
| Trajectory | `test_trajectory.py` | Acumula pontos até `max_length`; nunca cresce além |
| Motion (real, sem mock) | `test_motion.py` | Sem posição anterior → cinemática zerada; deslocamento horizontal/vertical/diagonal; aceleração (positiva e negativa) |
| ObjectState | `test_object_state.py` | `time_in_scene_frames` inclusivo; `to_dict()` completo, com/sem `previous_bbox` |
| WorldState | `test_world_state.py` | `to_dict()` serializa grupos de objetos + estatísticas |
| Registry | `test_registry.py` (world) | `BasicWorldModel` registrado; registrar um novo o disponibiliza |
| Factory | `test_factory.py` (world) | Nome desconhecido levanta exceção; falha de init é envolvida; resolve `basic` |
| `BasicWorldModel` (real, sem mock) | `test_world_model.py` | Criação de objeto novo (age=1); atualização incremental (age/frames_visible crescem); objeto desaparecendo → lost; reaparecendo → active de novo; `previous_bbox` correto; velocidade/aceleração computadas entre updates reais; limite de trajetória respeitado; limite de histórico respeitado; `WORKER_WORLD_MAX_OBJECTS` evict a mais antiga LOST primeiro (bug encontrado e corrigido, ver abaixo); `reset()` |
| `WorldModelProcessor` (mocka só o WorldModel) | `test_world_model_processor.py` | `is_enabled` exige os dois interruptores; no-op sem SceneAnalysisResult; atualiza e registra no contexto; `reset()` delega |
| Integração completa — World real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_world_model_enabled_produces_a_coherent_world_state` | Mocka só o Detector, Tracker/SceneAnalyzer/WorldModel REAIS produzem `WorldState` coerente: `track_id` estável, `age`/`frames_visible` corretos, `motion.speed>0`, `average_speed` correto |
| Reset entre Jobs (real, sem mock) | `test_basic_vision_engine.py::test_engine_resets_world_model_state_between_jobs` | A mesma instância processa 2 vídeos; `age` reinicia em 3 no segundo vídeo, não continua 6 |
| Configuração | `test_settings.py` | `test_settings_world_model_options_are_configurable` + extensão de defaults |
| Regressão | Todos os 179 testes anteriores (W1-W10) | Sem alteração de comportamento não intencional |

## Bug encontrado e corrigido durante a implementação

Ao escrever o teste de eviction (`WORKER_WORLD_MAX_OBJECTS`), descobri que `_evict_if_over_capacity()` removia corretamente objetos do `WorldModelContext` interno, mas a lista `lost_objects` já construída para o `WorldState` **daquele mesmo `update()`** não refletia a remoção — o objeto evictado ainda aparecia no `WorldState` retornado (removido internamente, mas "vazando" na fotografia do frame atual). **Corrigido** filtrando `lost_objects` contra `self._context.objects` logo após a eviction, antes de montar as estatísticas/`WorldState` finais.

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/ tests/` → só a mesma menção em docstring de sempre, nenhum `import` real cruzado.
- `grep -rn "yolo\|YOLO\|ByteTrack\|ultralytics\|cv2\|redis\|Redis\|backend_client\|r2_client" worker/inference/world/*.py` → só menções em docstring explicando que `WorldModel` NÃO conhece nenhum desses. Nenhum `import` real.
- Todos os `import`s reais de `worker/inference/world/*.py` conferidos manualmente: só módulos internos de `world/` + `worker.config.settings` + `worker.inference.events.types` (o único contrato de entrada permitido) + `worker.core.exceptions`. Nenhum `trackers/`, `detectors/`, `cv2`, `ultralytics`, `redis`.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/sessão da W7-W10. Gerei um vídeo real de 15 frames (640×480, 5fps) com uma bola se movendo continuamente (20px/frame), upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true` (`WORKER_WORLD_MAX_TRAJECTORY=10`). Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model']
object_count: 1, active_tracks: 1, lost_tracks: 0, average_speed: 20.0

world_state.frame_index: 14
  track_id=1 label=frisbee age=15 frames_visible=15 frames_hidden=0 active=True time_in_scene_frames=15
    position={'x': 379.0, 'y': 239.5} bbox={'x': 324,...} previous_bbox={'x': 304,...}
    motion={'displacement': 20.0, 'speed': 20.0, 'direction_degrees': 0.0, 'acceleration': -0.5}
    trajectory_len=10  (respeitando WORKER_WORLD_MAX_TRAJECTORY=10 mesmo com 15 frames processados)
  lost_objects: []
  recent_events count: 16
```

**Confirmado exatamente o que a sprint pediu — um WorldState coerente:** `track_id=1` estável do início ao fim (15 frames), `age`/`frames_visible` corretos, `bbox`/`previous_bbox` refletindo o deslocamento real (20px), `motion.speed=20.0`/`direction_degrees=0.0` (movimento puramente horizontal, correto) batendo com a velocidade real de geração do vídeo, `trajectory` truncada em exatamente 10 pontos apesar de 15 frames processados (limite configurado respeitado na prática), `average_speed=20.0` coerente. Lock liberado, mensagem confirmada (`XPENDING`=0). Stack derrubado ao final.

## Riscos (novos, registrados na Constituição - Seção 14)

20. **`ObjectState.time_in_scene_frames`/`Motion.speed` são expressos em frames, não em segundos** — consequência de o World Model nunca receber `fps`, só `frame_index`.
21. **`_evict_if_over_capacity()` pode remover um objeto genuíno momentaneamente perdido antes de ele se recuperar**, se `WORKER_WORLD_MAX_OBJECTS` for excedido por muitos objetos efêmeros simultaneamente — aceito por simplicidade; ajustar o limite para cima se necessário em produção.

## Preparação para a W12

A W12 ainda não tem escopo definido (qual análise específica de futebol entra primeiro). O que já está confirmado, pela repetição do mesmo padrão em W8/W9/W10/W11: uma nova camada de análise exige apenas um novo Processor + (se necessário) uma nova família de Registry/`factory.py` — nunca uma mudança em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `VideoReader`, Redis, Backend, R2, ou nas famílias de Plugin já existentes. A partir da W12, os analisadores de futebol consomem **exclusivamente** `WorldState` (via `context.world_states`/artefato `"world_state"`) — nunca `Detector`/`Tracker`/`SceneAnalyzer`/OpenCV/YOLO/ByteTrack diretamente. Esta é a primeira sprint em que regra de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
