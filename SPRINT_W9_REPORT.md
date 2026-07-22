# SPRINT_W9_REPORT.md — Goalkeeper AI Worker: Tracking API + Primeiro Tracker (ByteTrack)

> Escopo: introduzir a primeira camada de tracking real, isolada atrás de uma abstração própria (`Tracker`) desde o primeiro dia — ByteTrack é apenas a primeira implementação, nunca acoplado diretamente a nenhum Processor ou ao Detector. Ainda sem classificação, pose ou GPU. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W8_REPORT.md` antes de implementar.

- **`worker/inference/trackers/base.py`** (novo) — `Tracker` (ABC): contrato único `track(detections: DetectionResult) -> TrackingResult` + `reset()` (concreto, default no-op). `Tracker` conhece o contrato `DetectionResult` (a saída de QUALQUER Detector) — não conhece YOLO/Ultralytics especificamente.
- **`worker/inference/trackers/types.py`** (novo) — `TrackId`/`ClassLabel`/`Confidence` (`NewType`), `BoundingBox`, `TrackState` (enum `new`/`tracked`/`lost`/`removed`), `TrackedObject` (track_id/label/confidence/bbox/age/state/frame_index), `TrackingStatistics` (total/active/lost/removed_tracks), `TrackingResult` (+ `to_dict()`). Deliberadamente independentes dos tipos de `detectors/types.py` — mesma pequena duplicação já praticada entre `inference/types.py` e `detectors/types.py`.
- **`worker/inference/trackers/exceptions.py`** (novo) — `TrackerError` → `TrackerInitializationError`/`TrackerExecutionError`, ambas de `WorkerError`.
- **`worker/inference/trackers/registry.py`** (novo) — `register_tracker`/`get_tracker_class`/`available_trackers()`. Registry independente do de motores, Processors e Detectors — quatro Registries paralelos.
- **`worker/inference/trackers/factory.py`** (novo) — `create_tracker(nome, settings)`, espelhando `detectors/factory.py`.
- **`worker/inference/trackers/bytetrack_tracker.py`** (novo) — `ByteTrackTracker(Tracker)`: reaproveita `ultralytics.trackers.byte_tracker.BYTETracker` (já vendorizada como dependência transitiva desde a W8) em vez de trazer um pacote `bytetrack` separado. Um adaptador interno (`_DetectionsAdapter`, exclusivo deste arquivo) traduz `DetectionResult` para o formato "results-like" (`xywh`/`conf`/`cls` + indexação booleana) exigido por `BYTETracker.update()`, e a saída de volta (`[x1,y1,x2,y2,track_id,score,cls,idx]`) para `TrackingResult`. Mantém `_hit_counts` por `track_id` para computar `age` e aplicar `WORKER_TRACK_MIN_HITS`. `reset()` chama `BYTETracker.reset()` + limpa `_hit_counts`.
- **`worker/inference/processors/tracking_processor.py`** (novo) — `TrackingProcessor(FrameProcessor)`: **não detecta nem transforma a imagem**, só lê `context.detections[-1]` (o `DetectionResult` que `YOLOProcessor` acabou de produzir no MESMO frame), chama `Tracker.track()`, acumula o `TrackingResult` no contexto, propagando o `frame_index` correto. No-op seguro se `context.detections` estiver vazio (ex.: `YOLOProcessor` desabilitado). `is_enabled` reflete `settings.tracking_enabled and bool(settings.tracker)` — dois interruptores independentes de propósito. `reset()` delega a `self._tracker.reset()`.
- **`worker/inference/processors/base.py`** (estendido) — `ProcessorContext` ganhou `tracking_results: list[TrackingResult]` + `add_tracking_result`/`tracking_results_to_dict()`, mesmo padrão de `detections`/`add_detection_result` (W8). `FrameProcessor` ganhou `reset()` (concreto, default no-op).
- **`worker/inference/processors/pipeline.py`** — `PipelineProcessor.reset()` (novo): chama `processor.reset()` de cada Processor, sem saber qual deles tem estado.
- **`worker/inference/processors/registry.py`** — `TrackingProcessor` registrado por último (`color → resize → roi → statistics → yolo → tracking`).
- **`worker/inference/basic_vision_engine.py`** — chama `self._pipeline.reset()` no início de `process()` (ver achado arquitetural, abaixo); artefato ganha `"tracking_results"`, `"tracking_engine"`, `"tracking_statistics"`, `"tracking_time_ms"`.
- **`worker/config/settings.py`** — 5 campos novos: `tracker` (default `""`), `tracking_enabled` (default `False`), `track_min_confidence` (default `0.25`), `track_max_age` (default `30`), `track_min_hits` (default `1`).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `InferenceEngine.process`, `FrameProcessor.process`, `Detector.detect` são idênticos aos de antes; `PipelineState`, `Pipeline`, `Orchestrator`, `Redis`, `BackendClient`, `Storage`, `video/`, `Detector`, `YOLOProcessor` não mudaram uma linha (além do `reset()` genérico adicionado à ABC `FrameProcessor`, que `YOLOProcessor` não precisou sobrescrever).

## Achado arquitetural: estado entre Jobs (correção necessária)

Antes de escrever o `TrackingProcessor`, verifiquei como o `WorkerOrchestrator` instancia o motor de inferência (`orchestrator.py`): `self._inference = InferenceStage(create_engine(settings.inference_engine, settings))` roda **uma única vez**, em `__init__`, para todo o ciclo de vida do processo do Worker — não por Job. Isso significa que `BasicVisionEngine`, sua `PipelineProcessor` e cada `FrameProcessor` (incluindo um futuro `TrackingProcessor`/`ByteTrackTracker`) são **reaproveitados entre Jobs sequenciais**, nunca recriados.

Isso nunca importou para Color/Resize/ROI/Statistics/YOLO (todos stateless — cada chamada é independente), mas um `Tracker` é **inerentemente stateful**: sem correção, a mesma instância de `ByteTrackTracker` (com suas trilhas, filtro de Kalman e contador de `track_id` internos) continuaria acumulando estado de um vídeo para o próximo, completamente não relacionado — dois vídeos de goleiros diferentes processados em sequência pelo mesmo Worker teriam `TrackId`s contaminados.

**Corrigido** com um padrão `reset()` de duas camadas:
- `Tracker.reset()` (ABC, concreto, default no-op) — `ByteTrackTracker.reset()` limpa trilhas via `BYTETracker.reset()` + `_hit_counts`.
- `FrameProcessor.reset()` (ABC, concreto, default no-op) — `TrackingProcessor.reset()` delega a `self._tracker.reset()`.
- `PipelineProcessor.reset()` (novo) — chama `reset()` de cada Processor, sem saber qual deles de fato tem estado.
- `BasicVisionEngine.process()` chama `self._pipeline.reset()` no início, antes de abrir o vídeo.

O resultado: a instância já carregada (modelo/pesos, se houver) é reaproveitada sem custo de reinicialização, mas o estado de tracking é sempre limpo no início de cada Job. Validado por teste automatizado (`test_engine_resets_tracker_state_between_jobs`, ver Testes).

## Tracker API

```python
class Tracker(ABC):
    name: str
    version: str
    def __init__(self, settings: WorkerSettings) -> None: ...
    def track(self, detections: DetectionResult) -> TrackingResult: ...
    def reset(self) -> None: ...  # concreto, default no-op
```

`create_tracker(nome, settings)` resolve o Tracker ativo a partir de `WORKER_TRACKER`, espelhando `create_detector`. Trocar ByteTrack por BoT-SORT/DeepSORT/StrongSORT/OC-SORT: escrever uma nova classe que implemente `Tracker`, `register_tracker("x", XTracker)`, `WORKER_TRACKER=x` — sem tocar em `TrackingProcessor`, `PipelineProcessor`, `BasicVisionEngine`, `Detector`, `YOLOProcessor` ou qualquer outro módulo.

## ByteTrackTracker

Reaproveita `ultralytics.trackers.byte_tracker.BYTETracker` — a implementação de ByteTrack já vendorizada pela Ultralytics (usada internamente por `model.track()`), em vez de trazer um pacote `bytetrack`/`lap`/`cython_bbox` separado (historicamente difícil de instalar/compilar no Windows). Decisão pragmática, documentada como Risco 16: essa é uma API **interna**, não pública, do pacote — uma atualização futura do `ultralytics` que reestruture `ultralytics.trackers` quebraria `bytetrack_tracker.py` silenciosamente.

`_DetectionsAdapter` (exclusivo deste arquivo) expõe o protocolo "results-like" mínimo exigido por `BYTETracker.update()`: `.xywh` (Nx4, centro+dimensões), `.conf`, `.cls`, `__len__`, `__getitem__(mask booleana)`. Constrói esse adaptador a partir de `DetectionResult.detections` (convertendo `bbox` x/y/width/height → centro x/y/width/height). A saída de `update()` é um array Nx8 (`[x1,y1,x2,y2,track_id,score,cls,idx]` por linha) — `idx` aponta de volta para a posição na lista de detecções ORIGINAL deste frame, usado para recuperar o `label` real (não confiamos em ByteTrack para preservar rótulos string; passamos `cls=0` para todas as detecções e resolvemos o label via `idx`).

`age` é computado internamente (`_hit_counts[track_id]`, incrementado a cada chamada em que o `track_id` aparece) — usado tanto para popular `TrackedObject.age` quanto para aplicar `WORKER_TRACK_MIN_HITS` (trilhas com menos hits que o mínimo são suprimidas do resultado, mas continuam sendo contadas internamente pelo ByteTrack). `state` é `NEW` na primeira aparição de um `track_id`, `TRACKED` depois.

## TrackingProcessor

```
frame → TrackingProcessor.process()
    → context.detections vazio? → no-op, devolve (frame, metadata, context) inalterados
    → latest = context.detections[-1]   [DetectionResult do MESMO frame, produzido por YOLOProcessor mais cedo]
    → self._tracker.track(latest)
    → TrackingResult (frame_index e cada TrackedObject.frame_index corrigidos aqui)
    → context.add_tracking_result(result)
    → devolve (frame, metadata, context) inalterados - so associa, nunca transforma nem detecta
```

Registrado por último na pipeline (`color → resize → roi → statistics → yolo → tracking`) — sempre depois de `yolo`, associando exatamente as detecções que acabaram de ser produzidas no mesmo frame.

## Configuração

| Variável | Default | Efeito |
|---|---|---|
| `WORKER_TRACKER` | `""` (vazio) | Nome do Tracker ativo. Vazio = `TrackingProcessor` desabilitado. |
| `WORKER_TRACKING_ENABLED` | `false` | Interruptor mestre — precisa estar `true` **e** `WORKER_TRACKER` precisa apontar para um Tracker válido. |
| `WORKER_TRACK_MIN_CONFIDENCE` | `0.25` | Confiança mínima para iniciar uma nova trilha (mapeada para `track_high_thresh`/`new_track_thresh` do ByteTrack). |
| `WORKER_TRACK_MAX_AGE` | `30` | Frames que uma trilha perdida pode ficar sem correspondência antes de ser removida (mapeada para `track_buffer`). |
| `WORKER_TRACK_MIN_HITS` | `1` | Detecções consecutivas necessárias antes de uma trilha aparecer no artefato (1 = sem supressão). |

## Testes — 151/151 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Tipos | `test_types.py` (trackers) | `TrackingResult.to_dict()` serializa `tracked_objects`/`statistics` corretamente |
| Registry | `test_registry.py` (trackers) | `ByteTrackTracker` registrado; nome desconhecido devolve `None`; registrar um Tracker novo o disponibiliza |
| Factory | `test_factory.py` (trackers) | Nome desconhecido levanta `TrackerInitializationError`; falha de `__init__` é envolvida na mesma exceção; resolve `bytetrack` |
| `ByteTrackTracker` (real, sem mock) | `test_bytetrack_tracker.py` | Mesmo objeto mantém o mesmo `track_id` em 5 frames consecutivos; `age` incrementa corretamente (1,2,3); label/confidence corretos; estatísticas refletem trilhas ativas; `DetectionResult` vazio produz `tracked_objects=[]`; `reset()` limpa estado interno (nova trilha reinicia em `age=1`) |
| `TrackingProcessor` (mocka só o Tracker) | `test_tracking_processor.py` | `is_enabled` exige os dois interruptores; no-op quando não há detecção no frame; associa a última detecção e registra no contexto com `frame_index` correto; `reset()` delega ao Tracker |
| Integração completa — tracking real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_tracking_enabled_keeps_a_stable_track_id_across_frames` | Mocka só o Detector (objeto se movendo), Tracker REAL (ByteTrack) mantém `track_id` único em 5 frames, `age` incrementando `[1,2,3,4,5]`, `frame_index` correto em cada entrada, `tracking_statistics`/`tracking_engine`/`tracking_time_ms` corretos |
| Reset entre Jobs (real, sem mock) | `test_basic_vision_engine.py::test_engine_resets_tracker_state_between_jobs` | A mesma instância de `BasicVisionEngine` processa 2 vídeos em sequência; `age` reinicia em `[1,2,3]` no segundo vídeo, não continua `[4,5,6]` |
| Configuração | `test_settings.py` | `test_settings_tracker_options_are_configurable` + extensão de `test_settings_defaults_apply` |
| Regressão | Todos os 130 testes anteriores (W1-W8) | Sem alteração de comportamento não intencional |

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/ tests/` → só a mesma menção em docstring de sempre (`worker/__init__.py`), nenhum `import` real cruzado.
- `grep -rn "yolo\|YOLO" worker/inference/trackers/` → só menções em docstring explicando que Tracker NÃO conhece YOLO. Nenhum `import` real de `yolo_detector.py`/`ultralytics.YOLO`.
- `grep -rn "track\|Track" worker/inference/detectors/yolo_detector.py` → nenhuma ocorrência. `YOLODetector` não sabe que tracking existe.
- `PipelineProcessor` (`pipeline.py`) importa só `numpy`, `worker.config.settings`, `worker.inference.processors.{base,registry}`, `worker.video.metadata` — nenhuma biblioteca externa de IA/tracking.
- `BasicVisionEngine` (`basic_vision_engine.py`) importa só módulos internos do Worker — nenhum `cv2`/`ultralytics` direto.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/sessão da W7/W8. Gerei um vídeo real de 12 frames (640×480, 5fps) com um círculo vermelho se movendo horizontalmente (`cv2.circle`) e fiz upload real via `httpx`, disparando publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`, `WORKER_TRACKING_ENABLED=true`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`). YOLO11n classificou honestamente o círculo sintético como `"frisbee"` (não fabriquei nenhum resultado) — mas o que importa para a validação da W9 é a **persistência do `track_id`**:

```
tracking_engine: bytetrack
tracking_statistics: {'total_tracks': 1, 'active_tracks': 1, 'lost_tracks': 0, 'removed_tracks': 0}
processor_order: ['color', 'statistics', 'yolo', 'tracking']

frame 0:  [(1, 'frisbee', 1,  'new')]
frame 1:  [(1, 'frisbee', 2,  'tracked')]
frame 2:  [(1, 'frisbee', 3,  'tracked')]
...
frame 11: [(1, 'frisbee', 12, 'tracked')]
```

**Confirmado exatamente o que a sprint pediu:** o mesmo objeto manteve o mesmo `TrackId=1` do início ao fim (12 frames), `age` incrementando de 1 a 12, estado transicionando `new → tracked`, estatísticas finais corretas (1 trilha total/ativa, 0 perdidas/removidas). Lock liberado (`GET lock:video:...` vazio), mensagem confirmada (`XPENDING` = 0 pendentes). Stack derrubado (`docker compose down`) ao final.

## Riscos (novos, registrados na Constituição - Seção 14)

16. **`ByteTrackTracker` acopla-se a uma API interna, não pública, do `ultralytics`** — o protocolo "results-like" que `_DetectionsAdapter` imita pode mudar em versões futuras sem aviso, diferente da API pública estável `model.track()`.
17. **Qualquer Processor futuro com estado próprio precisa lembrar de implementar `reset()` corretamente** — convenção, não imposta além do default no-op da ABC; mesma classe de risco dos itens 11/12 (convenções de construtor/`is_enabled` não impostas pelo compilador).

## Preparação para a W10

A W10 ainda não tem escopo definido nesta revisão (pose estimation, classificação de ação, ou outra camada). O que já está confirmado, pela repetição do mesmo padrão em W8 (Detecção) e W9 (Tracking): uma nova camada de análise exige apenas um novo Processor + (se envolver algoritmo substituível) uma nova família de Registry/`factory.py` — nunca uma mudança em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `VideoReader`, Redis, Backend, R2, ou nas famílias de Plugin já existentes. Se a nova camada for stateful, `AI_WORKER_CONSTITUTION.md` já documenta o padrão `reset()` a seguir (Risco 17), evitando redescobrir o mesmo problema na prática.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
