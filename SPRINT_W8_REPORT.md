# SPRINT_W8_REPORT.md — Goalkeeper AI Worker: Detection API + Primeiro Detector (YOLO)

> Escopo: introduzir a primeira camada de detecção real, isolada atrás de uma abstração própria (`Detector`) desde o primeiro dia — YOLO é apenas a primeira implementação, nunca acoplado diretamente a nenhum Processor. Ainda sem tracking, classificação, pose ou GPU. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `SPRINT_W7_REPORT.md` e o código real de `processors/`/`frame_ops.py` antes de implementar.

- **`worker/inference/detectors/base.py`** (novo) — `Detector` (ABC): contrato único `detect(frame) -> DetectionResult`. Construído como `classe(settings)` (mesma convenção uniforme de Engines/Processors).
- **`worker/inference/detectors/types.py`** (novo) — `BoundingBox` (x/y/width/height), `ClassLabel`/`Confidence` (`NewType` de `str`/`float` — identidade em runtime, só nomeiam o domínio, sem overhead de wrapper), `Detection` (label/confidence/bbox), `DetectionResult` (lista de `Detection` + frame_index/model_name/model_version/duration_ms + `to_dict()`). Distintos dos tipos de `inference/types.py` (artefato final do motor).
- **`worker/inference/detectors/exceptions.py`** (novo) — `DetectorError` → `DetectorInitializationError`/`DetectorExecutionError`, ambas de `WorkerError`.
- **`worker/inference/detectors/registry.py`** (novo) — `register_detector`/`get_detector_class`/`available_detectors()`. Registry independente do de motores e do de Processors — três Registries paralelos, um por família de Plugin.
- **`worker/inference/detectors/factory.py`** (novo) — `create_detector(nome, settings)`, espelhando `inference/engine.py`; envolve qualquer falha de inicialização numa `DetectorInitializationError`.
- **`worker/inference/detectors/yolo_detector.py`** (novo) — `YOLODetector(Detector)`: primeira implementação real, usando Ultralytics YOLO. **Todo código Ultralytics vive exclusivamente aqui** — carrega o modelo (`settings.model_path`), roda `model.predict(frame, conf=..., iou=...)`, converte a saída (`boxes.xyxy`/`cls`/`conf`/`names`) para `DetectionResult`.
- **`worker/inference/processors/yolo_processor.py`** (novo) — `YOLOProcessor(FrameProcessor)`: **não transforma a imagem**, só chama `create_detector(settings.detector, settings).detect(frame)`, injeta o `frame_index` no resultado e o acumula no contexto. Nenhuma linha de Ultralytics, pesos ou modelo aqui — só o contrato `Detector`. `is_enabled` reflete `bool(settings.detector)` — vazio (padrão) desabilita sem tentar carregar nenhum modelo.
- **`worker/inference/processors/base.py`** (estendido) — `ProcessorContext` ganhou `detections: list[DetectionResult]` + `add_detection_result(result)`/`detections_to_dict()`, generalizando o mesmo padrão de acúmulo já usado por `stats` desde a W7.
- **`worker/inference/processors/registry.py`** — `YOLOProcessor` registrado por último (`color → resize → roi → statistics → yolo`) — detecta sobre o frame já pré-processado pelos demais.
- **`worker/inference/basic_vision_engine.py`** — acrescenta `payload["detection_results"] = context.detections_to_dict()` ao artefato. Continua sem saber nada de detecção além de ler `context.detections` de volta — mesma disciplina de `context.stats` desde a W7.
- **`worker/config/settings.py`** — 4 campos novos: `detector` (default `""` — YOLOProcessor desabilitado), `model_path` (default `"weights/yolo11n.pt"`), `confidence_threshold` (default `0.25`), `iou_threshold` (default `0.45`). `model_config` ganhou `protected_namespaces=()` para silenciar um falso-positivo do pydantic (`model_path` colide com o namespace reservado `model_*` do próprio pydantic — sem conflito real de atributo).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `InferenceEngine.process(state) -> state` e `FrameProcessor.process(frame, metadata, context)` são idênticos aos de antes; `PipelineState`, `Pipeline`, `Orchestrator`, `Redis`, `BackendClient`, `Storage`, `video/`, `PipelineProcessor` não mudaram uma linha.

## Detector API

Contrato mínimo, independente de framework:

```python
class Detector(ABC):
    name: str
    version: str
    def __init__(self, settings: WorkerSettings) -> None: ...
    def detect(self, frame: np.ndarray) -> DetectionResult: ...
```

`create_detector(nome, settings)` resolve o Detector ativo a partir de `WORKER_DETECTOR`, espelhando `create_engine`/`PipelineProcessor.from_settings()`. Trocar YOLO por RT-DETR/GroundingDINO/OWLv2: escrever uma nova classe que implemente `Detector`, `register_detector("x", XDetector)`, `WORKER_DETECTOR=x` — sem tocar em `YOLOProcessor`, `PipelineProcessor`, `BasicVisionEngine` ou qualquer outro módulo.

## YOLODetector

Carrega o modelo (`ultralytics.YOLO(settings.model_path)`) no `__init__` — falha de carregamento vira `DetectorInitializationError`. `detect()` chama `model.predict(frame, conf=confidence_threshold, iou=iou_threshold, verbose=False)`, converte cada caixa (`xyxy`/`cls`/`conf`) para `Detection` (label via `result.names`, bbox em x/y/width/height), embrulha em `DetectionResult` com `duration_ms` medido. Falha durante a inferência vira `DetectorExecutionError`. Roda inteiramente em CPU (`torch` CPU-only, sem CUDA/ROCm) — consistente com a proibição de GPU nesta sprint.

## YOLOProcessor

```
frame → YOLOProcessor.process()
    → create_detector(settings.detector, settings).detect(frame)   [1x por Processor, cacheado no __init__]
    → DetectionResult (frame_index ainda 0, injetado aqui)
    → context.add_detection_result(result)
    → devolve (frame, metadata, context) inalterados - so detecta, nunca transforma
```

Registrado por último na pipeline (`color → resize → roi → statistics → yolo`) — quando resize/ROI estão habilitados, a detecção roda sobre o frame já normalizado.

## Modelo

`YOLO11n` (pequeno, ~5.6MB), baixado automaticamente pela Ultralytics no primeiro uso e armazenado em `weights/yolo11n.pt` — pasta já reservada e não versionada no git desde a W5 (`.gitignore` ganhou também `*.pt`, defensivamente, caso algum download futuro escape do CWD esperado). `WORKER_MODEL_PATH` aponta para lá por padrão; qualquer outro caminho/checkpoint é configurável sem mudar código.

## Configuração

| Variável | Default | Efeito |
|---|---|---|
| `WORKER_DETECTOR` | `""` (vazio) | Nome do Detector ativo. Vazio = `YOLOProcessor` desabilitado, nenhum modelo carregado. `"yolo"` habilita. |
| `WORKER_MODEL_PATH` | `weights/yolo11n.pt` | Caminho/nome dos pesos usados pelo Detector ativo. |
| `WORKER_CONFIDENCE_THRESHOLD` | `0.25` | Confiança mínima para manter uma detecção. |
| `WORKER_IOU_THRESHOLD` | `0.45` | Limiar de IoU do NMS. |

## Dependência nova — `ultralytics`

Adicionada a `requirements.txt` (traz `torch`/`torchvision` CPU-only — confirmado `torch.cuda.is_available() is False`, nenhuma linha de CUDA/ROCm tocada). Dois efeitos colaterais reais tratados nesta sprint (documentados como Riscos 13/14/15, Seção 14 da Constituição):

1. **Conflito `opencv-python` vs. `opencv-python-headless`** — `ultralytics` traz `opencv-python` (variante com GUI) como dependência transitiva, que colide no mesmo diretório `cv2/` com `opencv-python-headless` (a variante deliberadamente escolhida desde a W5, sem dependências gráficas). Resolvido: desinstalar `opencv-python`, reinstalar `opencv-python-headless` por cima. `pip check` reporta permanentemente "ultralytics requires opencv-python, which is not installed" — falso positivo aceito, documentado.
2. **NumPy 1.x → 2.x** — `ultralytics` exige NumPy 2.x, incompatível em nível de ABI binária com `opencv-python-headless==4.9.0.80` (compilado contra NumPy 1.x). Resolvido: `opencv-python-headless` atualizado para `4.10.0.84` (primeira versão com suporte a NumPy 2.x). `requirements.txt` atualizado (`numpy==2.2.6`, `opencv-python-headless==4.10.0.84`). Suite completa (130 testes, incluindo todos os de `video/`/`frame_ops.py` herdados de W5/W6/W7) validada passando após a migração.

## Arquivos criados

`worker/inference/detectors/__init__.py`, `base.py`, `types.py`, `exceptions.py`, `registry.py`, `factory.py`, `yolo_detector.py`; `worker/inference/processors/yolo_processor.py`.

Testes novos: `tests/inference/detectors/__init__.py`, `test_types.py`, `test_registry.py`, `test_factory.py`, `test_yolo_detector.py`; `tests/inference/processors/test_yolo_processor.py`.

## Arquivos alterados

- `worker/inference/processors/base.py` — `ProcessorContext.detections`/`add_detection_result`/`detections_to_dict()`.
- `worker/inference/processors/registry.py` — registra `YOLOProcessor`.
- `worker/inference/basic_vision_engine.py` — artefato ganha `"detection_results"`; docstring atualizada.
- `worker/config/settings.py` — 4 campos novos + `protected_namespaces=()`.
- `requirements.txt` — `ultralytics==8.4.104`; `numpy` e `opencv-python-headless` atualizados por compatibilidade.
- `.gitignore` — `*.pt` adicionado (defensivo, além de `/weights/` já existente).
- `.env.example` — novas variáveis documentadas.
- `tests/inference/processors/test_registry.py` — lista esperada de Processors inclui `"yolo"`.
- `tests/inference/test_basic_vision_engine.py` — `detection_results` no teste de shape do artefato + novo teste de integração completa com YOLO real.
- `tests/test_settings.py` — novo teste (`test_settings_detector_options_are_configurable`) + extensão de `test_settings_defaults_apply`.
- **`AI_WORKER_CONSTITUTION.md`** — atualizada **durante** esta sprint (§1 tabela `inference`, §6 tabela de Registries + Detector Registry, §6.1 reescrita com a API de Detecção, §7 nota sobre CPU-only, §12 árvore, §13 Roadmap: W8 concluída + nova linha W9, §14 três novos riscos (13/14/15), §15/§16: W8 histórico, W9 vira a preparação para Tracking).

## Testes — 130/130 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Tipos | `test_types.py` | `DetectionResult.to_dict()` serializa bbox/detections corretamente; resultado vazio por padrão |
| Registry | `test_registry.py` (detectors) | `YOLODetector` registrado; nome desconhecido devolve `None`; registrar um Detector novo o disponibiliza |
| Factory | `test_factory.py` | Nome desconhecido levanta `DetectorInitializationError`; falha de `__init__` de um Detector é envolvida na mesma exceção |
| `YOLODetector` (real, sem mock) | `test_yolo_detector.py` | `detect()` sobre um frame sintético devolve `DetectionResult` bem formado; respeita `confidence_threshold`/`iou_threshold` configurados |
| `YOLOProcessor` (mocka só o Detector) | `test_yolo_processor.py` | `is_enabled` reflete `WORKER_DETECTOR`; `process()` não transforma o frame, registra no contexto, injeta `frame_index` correto |
| Integração completa (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_yolo_processor_enabled_produces_real_detection_results` | Artefato real (YOLO11n de verdade) contém `"yolo"` em `processor_order`, `detection_results` com um `DetectionResult` por frame, `frame_index` correto em cada um |
| Regressão | Todos os 117 testes anteriores (W1-W7) | Sem alteração de comportamento não intencional — inclusive após a migração de NumPy 1.x → 2.x |

**Nota sobre mocks:** seguindo a diretriz da sprint, `YOLODetector` é testado com o modelo **real** (a única forma de provar que a conversão Ultralytics → `DetectionResult` de fato funciona); já `YOLOProcessor` e a integração de pipeline mais ampla usam um `Detector` real de verdade também no teste de integração final, e um `_StubDetector` (mock só da inferência, nunca do resto do fluxo) no teste unitário do Processor — restante do fluxo (frame/metadata/context reais) sempre real.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/sessão da W7 (`treinador-w7@example.com`), gerei um vídeo real de 15 frames (320×240, 10fps) com OpenCV (um retângulo sólido — sem pretensão de ser detectável como objeto COCO real) e fiz upload real via `httpx`, disparando publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_MODEL_PATH=weights/yolo11n.pt`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```json
{
  "frames_processed": 15, "frame_skip": 0,
  "processors": {"color": {...}, "statistics": {...}, "yolo": {"frames_processed": 15, "total_time_ms": 2360.0}},
  "processor_order": ["color", "statistics", "yolo"],
  "detection_results": [
    {"frame_index": 0, "model_name": "yolo", "model_version": "1.0.0", "duration_ms": 1797.0, "detections": []},
    {"frame_index": 1, "model_name": "yolo", "model_version": "1.0.0", "duration_ms": 47.0, "detections": []},
    "... (13 entradas seguintes, uma por frame, indices 2-14 em ordem)"
  ]
}
```

Confirmado: 15 `DetectionResult` reais (um por frame, `frame_index` 0-14 em ordem), `duration_ms` do primeiro frame reflete o *warm-up* real do modelo (~1.8s), os seguintes ~30-47ms (perfil esperado de CPU); `detections: []` em todos porque o vídeo sintético não contém nenhuma classe COCO real — resultado correto, não um erro (prova que a integração é genuína, não fabricada). `processor_order` confirma `yolo` executando por último. Lock liberado (`GET lock:video:...` vazio), mensagem confirmada (`XPENDING` = 0 pendentes). Stack derrubado (`docker compose down`) ao final.

Boundary Enforcement re-verificado: `grep -rn "backend_fastapi\|frontend_flutter" worker/ tests/` só encontra a mesma menção em docstring de sempre (`worker/__init__.py`), nenhum `import` real cruzado.

## Preparação para a W9 (Tracking)

Confirmado na prática: adicionar detecção real exigiu **apenas** um novo Processor (`YOLOProcessor`) + uma nova família de Registry/factory (`inference/detectors/`) — zero alteração em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `video/`, Redis, Backend ou R2. A W9 repete esse encaixe para Tracking, consumindo `context.detections` (já real e disponível desde esta sprint):

1. Definir `Tracker` (abstração análoga a `Detector`) em `inference/trackers/`, com Registry e `factory.py` próprios.
2. Escrever `ByteTrackTracker(Tracker)` (ou outro), todo código do framework de tracking exclusivamente ali.
3. Escrever `TrackingProcessor(FrameProcessor)`, registrado depois de `yolo`, consumindo `context.detections` do frame atual.
4. Habilitar via `WORKER_TRACKER=bytetrack`, sem tocar em `YOLOProcessor`, `PipelineProcessor` ou `BasicVisionEngine`.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
