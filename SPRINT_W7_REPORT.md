# SPRINT_W7_REPORT.md — Goalkeeper AI Worker: Pipeline de Processamento de Visão (Processors)

> Escopo: decompor a transformação de frame do `BasicVisionEngine` em `Processors` independentes, compostos por um `PipelineProcessor`. Ainda sem YOLO, MediaPipe, OpenPose, OCR, tracking, GPU/CUDA/ROCm/TensorRT. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `SPRINT_W6_REPORT.md` e o código real de `basic_vision_engine.py`/`frame_ops.py` antes de implementar.

- **`worker/inference/processors/base.py`** (novo) — `FrameProcessor` (ABC): contrato único `process(frame, metadata, context) -> (frame, metadata, context)` + `is_enabled(settings)` (classmethod). **Nenhum Processor conhece outro Processor.** `ProcessorStats`/`ProcessorContext` acumulam tempo de execução e frames processados por Processor, com `to_dict()` para o artefato.
- **`worker/inference/processors/color_processor.py`** (novo) — `ColorProcessor`, converte BGR→RGB delegando a `frame_ops.convert_bgr_to_rgb`. `is_enabled` reflete `WORKER_ENABLE_COLOR_PROCESSOR` (default `true`).
- **`worker/inference/processors/resize_processor.py`** (novo) — `ResizeProcessor`, delega a `frame_ops.resize_frame`. `is_enabled` reflete `WORKER_ENABLE_RESIZE`.
- **`worker/inference/processors/roi_processor.py`** (novo) — `ROIProcessor`, delega a `frame_ops.apply_roi`. `is_enabled` reflete `WORKER_ENABLE_ROI`.
- **`worker/inference/processors/statistics_processor.py`** (novo) — `StatisticsProcessor`, não transforma a imagem, só registra métricas via `context.record(...)`. `is_enabled` reflete `WORKER_ENABLE_STATISTICS_PROCESSOR` (default `true`).
- **`worker/inference/processors/registry.py`** (novo) — Registry independente do de motores (`inference/registry.py`): `register_processor`/`get_processor_class`/`available_processors()`. Ordem de registro (`color → resize → roi → statistics`) define a ordem de execução por padrão — usa `dict` comum (preserva ordem de inserção).
- **`worker/inference/processors/pipeline.py`** (novo) — `PipelineProcessor`: única responsabilidade é **executar** a sequência de Processors habilitados; expõe `processor_names` e `from_settings(settings)` (fábrica que consulta `available_processors()` + `is_enabled()` de cada um).
- **`worker/inference/basic_vision_engine.py`** (reescrito, `1.0.0` → `2.0.0`) — deixou de chamar `cv2.cvtColor`/`resize`/recorte diretamente. Agora: abre o vídeo, itera frames, decide **apenas** se um frame entra na pipeline (`WORKER_FRAME_SKIP` — decisão do engine, não de um Processor: "decidir SE um frame entra na pipeline é diferente de TRANSFORMAR um frame"), delega toda transformação a `PipelineProcessor`, monta `InferenceResult` + artefato JSON com duas chaves novas: `"processors"` (métricas de `context.to_dict()`) e `"processor_order"` (`pipeline.processor_names`).
- **De-duplicação (achado durante a implementação):** os três Processors de transformação (`Color`/`Resize`/`ROI`) **não reimplementam** a lógica de pixel — cada um empacota `frame`+`metadata` num `Frame` e chama a função pura correspondente já existente em `frame_ops.py` (Sprint W6), evitando duplicar `cv2.cvtColor`/`cv2.resize`/recorte entre a camada de Processors e `frame_ops`.
- **`worker/config/settings.py`** — 2 campos novos, opcionais: `enable_color_processor`/`enable_statistics_processor` (ambos default `true`).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `InferenceEngine.process(state) -> state` é idêntico ao da W4; `PipelineState`, `Pipeline`, `Orchestrator`, `Redis`, `BackendClient`, `Storage`, `video/` não mudaram uma linha.

## Fluxo atualizado

```
Redis → ... → DownloadVideoStage → InferenceStage
    → BasicVisionEngine.process(state)   [v2.0.0 - orquestrador fino desde a W7]
        → VideoReader(state.download_path) [abre, valida]
        → PipelineProcessor.from_settings(settings)  [monta a sequencia habilitada]
        → for frame in FrameIterator(FrameProvider(reader)):
              se should_process(frame_index):  # respeita WORKER_FRAME_SKIP - decisao do engine
                  pipeline.process(frame.image, frame.metadata, context)
                      → ColorProcessor.process(...)      [se habilitado]
                      → ResizeProcessor.process(...)     [se habilitado]
                      → ROIProcessor.process(...)         [se habilitado]
                      → StatisticsProcessor.process(...)   [se habilitado]
                  frames_processed += 1
        → InferenceResult (frame_metadata real + frames_processed + frame_skip + roi)
        → artifact.json  { ...InferenceResult.to_dict(), "processors": context.to_dict(),
                            "processor_order": pipeline.processor_names }
→ UploadArtifactStage → UpdateStatusStage → [finally] CleanupStage → ReleaseLockStage → ACK
```

## Processors

| Processor | Transforma? | Delega a | Habilitado por | Default |
|---|---|---|---|---|
| `ColorProcessor` (`"color"`) | Sim (BGR→RGB) | `frame_ops.convert_bgr_to_rgb` | `WORKER_ENABLE_COLOR_PROCESSOR` | `true` |
| `ResizeProcessor` (`"resize"`) | Sim (redimensiona) | `frame_ops.resize_frame` | `WORKER_ENABLE_RESIZE` | `false` |
| `ROIProcessor` (`"roi"`) | Sim (recorta) | `frame_ops.apply_roi` | `WORKER_ENABLE_ROI` | `false` |
| `StatisticsProcessor` (`"statistics"`) | Não (só mede) | — | `WORKER_ENABLE_STATISTICS_PROCESSOR` | `true` |

## Pipeline

`PipelineProcessor.from_settings()` monta a sequência consultando `available_processors()` (ordem de registro: `color, resize, roi, statistics`) e filtrando pelos `is_enabled(settings)` de cada um. Um Processor desabilitado simplesmente não aparece na lista nem no artefato. Adicionar um novo Processor não exige alterar `pipeline.py` — só registrá-lo em `processors/registry.py`.

## Arquivos criados

`worker/inference/processors/__init__.py`, `base.py`, `color_processor.py`, `resize_processor.py`, `roi_processor.py`, `statistics_processor.py`, `registry.py`, `pipeline.py`.

Testes novos: `tests/inference/processors/__init__.py`, `test_color_processor.py`, `test_resize_processor.py`, `test_roi_processor.py`, `test_statistics_processor.py`, `test_registry.py`, `test_pipeline.py`.

## Arquivos alterados

- `worker/inference/basic_vision_engine.py` — reescrito como orquestrador fino (v1.0.0 → v2.0.0).
- `worker/config/settings.py` — 2 campos novos (`enable_color_processor`/`enable_statistics_processor`).
- `.env.example` — novas variáveis documentadas.
- `tests/inference/test_basic_vision_engine.py` — novo teste de integração (`test_engine_is_a_thin_orchestrator_over_the_processor_pipeline`).
- `tests/test_settings.py` — novo teste (`test_settings_processor_toggles_are_configurable`) + extensão de `test_settings_defaults_apply`.
- **`AI_WORKER_CONSTITUTION.md`** — atualizada **durante** esta sprint (Seção 6 tabela de Registries, 6.1 reescrita, 1, 12, 13, 14 novo risco #12, 15/16 reorganizadas: W7 histórico, W8 vira a preparação para o primeiro detector real).

## Testes — 117/117 passando

| Categoria | Onde | O que valida |
|---|---|---|
| `ColorProcessor` | `test_color_processor.py` | `is_enabled` reflete config; `process` converte cor e registra contexto |
| `ResizeProcessor` | `test_resize_processor.py` | `is_enabled` reflete config; `process` redimensiona e atualiza metadados |
| `ROIProcessor` | `test_roi_processor.py` | Idem, para recorte |
| `StatisticsProcessor` | `test_statistics_processor.py` | Imagem/metadados permanecem idênticos (`result_image is image`) |
| Registry | `test_registry.py` | Os 4 Processors padrão estão registrados; ordem de registro define ordem de execução (`test_registration_order_defines_pipeline_order`); troca por um Processor de teste, com limpeza `try/finally` (ver Erros) |
| Pipeline — execução/ordem | `test_pipeline.py` | Pipeline padrão roda só `color`/`statistics`; habilitar resize/ROI produz `["color","resize","roi","statistics"]`; desabilitar tudo produz `[]`; contexto acumula estatísticas por Processor |
| Integração completa | `test_basic_vision_engine.py::test_engine_is_a_thin_orchestrator_over_the_processor_pipeline` | Artefato real contém `processor_order` e `processors` corretos; Processor desabilitado (`roi`) não aparece |
| Regressão | Todos os 98 testes anteriores (W1-W6) | Sem alteração de comportamento não intencional |

## Erro encontrado e corrigido durante a implementação

Ao escrever `test_registry.py`, registrar um `_DummyProcessor` de teste (`register_processor("dummy-test-processor", ...)`) poluiria **permanentemente** o dict global `_PROCESSORS` pelo resto da sessão do pytest — diferente do teste análogo em `inference/registry.py` (motores), que é inofensivo porque nada itera automaticamente todos os motores registrados. Como `PipelineProcessor.from_settings()` itera `available_processors()` e inclui qualquer Processor com `is_enabled()==True`, um dummy vazado apareceria silenciosamente em toda pipeline montada depois no mesmo processo de teste (quebrando asserções de lista exata em `test_basic_vision_engine.py`). **Corrigido** com `try/finally`, removendo `"dummy-test-processor"` de `_PROCESSORS` ao final do teste.

## Validação manual — stack real

Subi o stack real (`docker compose up --build`: Postgres + Redis + backend), criei um usuário/goleiro/sessão reais via API (`treinador-w7@example.com`, clube já existente `Clube W2`), gerei um vídeo real de 30 frames (10fps, 64×48) com OpenCV e fiz upload real via `httpx` (multipart — nunca `curl`, bug conhecido do Git Bash no Windows), disparando publicação real no Redis (`XLEN processing_jobs` confirmado).

Rodei `python -m worker.main` com `WORKER_FRAME_SKIP=2`, `WORKER_ENABLE_RESIZE=true` (`32×24`), `WORKER_ENABLE_ROI=true` (`x=2,y=2,20×16`), `WORKER_ENABLE_COLOR_PROCESSOR=true`, `WORKER_ENABLE_STATISTICS_PROCESSOR=true` — exercitando os 4 Processors na mesma execução. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`, só para verificação — nunca no código do Worker):

```json
{"status": "processed", "detections": [], "frame_metadata": {"frame_count": 30, "width": 20, "height": 16, "fps": 10.0, "duration_seconds": 3.0}, "metadata": {"engine_name": "basic_vision", "engine_version": "2.0.0", "duration_ms": 15.0}, "frames_processed": 10, "frame_skip": 2, "roi": {"x": 2, "y": 2, "width": 20, "height": 16}, "processors": {"color": {"frames_processed": 10, "total_time_ms": 0.0}, "resize": {"frames_processed": 10, "total_time_ms": 0.0}, "roi": {"frames_processed": 10, "total_time_ms": 0.0}, "statistics": {"frames_processed": 10, "total_time_ms": 0.0}}, "processor_order": ["color", "resize", "roi", "statistics"]}
```

Confirmado: `frames_processed=10` (30 frames, skip=2 → índices 0,3,…,27), resolução final `20×16` (ROI aplicada por último, sobrepondo o resize de `32×24`), `processor_order` reflete exatamente a ordem registrada, `processors` mostra os 4 executando 10 frames cada. Também confirmado via `redis-cli`: Lock liberado (`GET lock:video:...` vazio) e mensagem confirmada (`XPENDING processing_jobs goalkeeper_ai_worker` = 0 pendentes); via API: vídeo com `upload_status=UPLOADED`. Stack derrubado (`docker compose down`) ao final.

Boundary Enforcement re-verificado: `grep -rn "backend_fastapi\|frontend_flutter" worker/ tests/` só encontra uma menção em docstring (`worker/__init__.py`), nenhum `import` real cruzado.

## Preparação para a W8 (primeiro detector real)

Confirmado na prática: a W7 prova que uma nova unidade de transformação de frame (um Processor) se encaixa na pipeline sem alterar `BasicVisionEngine`, `Pipeline`, `Orchestrator` ou `VideoReader`. A W8 repete exatamente esse encaixe, trocando "medir/normalizar" por "detectar objetos":

1. Escrever `YOLOProcessor(FrameProcessor)` em `worker/inference/processors/`, implementando `process(frame, metadata, context)` e `is_enabled(settings)`.
2. `register_processor("yolo", YOLOProcessor)` em `processors/registry.py`.
3. Habilitar via `WORKER_ENABLE_YOLO_PROCESSOR` no `.env`.

Nenhuma alteração em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator` ou `VideoReader`. `AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
