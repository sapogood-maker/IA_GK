# SPRINT_W6_REPORT.md — Goalkeeper AI Worker: Primeiro Motor Real de Visão (`BasicVisionEngine`)

> Escopo: construir uma camada de visão computacional reutilizável — resize, ROI, frame skipping, conversão de cor, estatísticas básicas. Ainda sem YOLO, MediaPipe, OpenPose, OCR, segmentação, tracking, classificação, GPU/CUDA/ROCm/TensorRT ou batch inference. **Nova regra vigente a partir desta sprint: sem mais sprints de sincronização (Wx.1) — `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os 9 ADRs e `SPRINT_W5_REPORT.md` antes de implementar.

- **`worker/inference/frame_ops.py`** (novo) — `convert_bgr_to_rgb`, `resize_frame`, `apply_roi`: funções puras (nunca mutam o `Frame` de entrada), reutilizáveis por **qualquer** motor, não só `BasicVisionEngine`.
- **`worker/inference/basic_vision_engine.py`** (novo) — `BasicVisionEngine(InferenceEngine)`, motor **padrão** desde esta sprint (`WORKER_INFERENCE_ENGINE=basic_vision`). Internamente: abre o vídeo com `video.VideoReader`, itera com `FrameProvider`/`FrameIterator`, aplica `frame_skip` (via `VisionEngineConfig.should_process`), converte BGR→RGB, aplica resize/ROI quando configurados, acumula `frames_processed` e a resolução final. **Nenhuma detecção.**
- **`worker/inference/types.py`** (estendido) — novo tipo `RegionOfInterest` (x/y/width/height); `InferenceResult` ganhou `frames_processed`/`frame_skip`/`roi`, todos opcionais (`None` por padrão) — **não quebra `FakeInferenceEngine`**, que nunca os preenche.
- **`worker/inference/fake_engine.py`** — ganhou `__init__(settings)` (ignorado) só para manter o mesmo formato de construtor de qualquer motor registrado; deixou de ser o motor padrão, permanece **exclusivamente para testes**.
- **`worker/inference/registry.py`/`engine.py`** — `"basic_vision"` registrado; `create_engine(nome, settings)` agora **sempre** passa `settings` ao construtor do motor (convenção uniforme — documentada como risco 11 na Constituição, já que não é imposta pela ABC).
- **`worker/config/settings.py`** — `inference_engine` default mudou de `"fake"` para `"basic_vision"`; 9 campos novos, todos opcionais: `frame_skip`, `enable_resize`/`target_width`/`target_height`, `enable_roi`/`roi_x`/`roi_y`/`roi_width`/`roi_height`.

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `InferenceEngine.process(state) -> state` é idêntico ao da W4; `PipelineState`, `Pipeline`, `Orchestrator`, `Redis`, `BackendClient`, `Storage`, `video/` não mudaram uma linha.

## Fluxo atualizado

```
Redis → ... → DownloadVideoStage → InferenceStage
    → BasicVisionEngine.process(state)   [motor padrao desde a W6]
        → VideoReader(state.download_path) [abre, valida]
        → for frame in FrameIterator(FrameProvider(reader)):
              se should_process(frame_index):  # respeita WORKER_FRAME_SKIP
                  convert_bgr_to_rgb(frame)
                  resize_frame(...) se WORKER_ENABLE_RESIZE
                  apply_roi(...) se WORKER_ENABLE_ROI
                  frames_processed += 1
        → InferenceResult (frame_metadata real + frames_processed + frame_skip + roi)
        → artifact.json
→ UploadArtifactStage → UpdateStatusStage → [finally] CleanupStage → ReleaseLockStage → ACK
```

## Arquivos criados

`worker/inference/frame_ops.py`, `worker/inference/basic_vision_engine.py`.

Testes novos: `tests/inference/test_frame_ops.py`, `tests/inference/test_basic_vision_engine.py`.

## Arquivos alterados

- `worker/inference/types.py` — `RegionOfInterest` + extensão de `InferenceResult`.
- `worker/inference/fake_engine.py` — `__init__(settings)` opcional.
- `worker/inference/registry.py` — registra `BasicVisionEngine`.
- `worker/inference/engine.py` — `create_engine(nome, settings)`.
- `worker/orchestrator/orchestrator.py` — passa `settings` a `create_engine`.
- `worker/config/settings.py` — 9 campos novos + default do motor.
- `requirements.txt` — sem novas dependências (OpenCV/numpy já vieram na W5).
- `.env.example` — novas variáveis documentadas.
- `tests/test_settings.py`, `tests/inference/test_registry.py`, `tests/infrastructure/test_orchestrator_pipeline.py` — atualizados para o novo motor padrão e assinatura de `create_engine`.
- **`AI_WORKER_CONSTITUTION.md`** — atualizada **durante** esta sprint (Seções 1, 6.1, 6.3 nova, 12, 13, 14, 15/16 reorganizadas), conforme a nova regra.

## Testes — 98/98 passando

| Categoria | Onde | O que valida |
|---|---|---|
| `frame_ops` | `tests/inference/test_frame_ops.py` | Conversão de cor, resize, ROI — todas puras, nunca mutam o frame original |
| Frame skipping | `tests/inference/test_basic_vision_engine.py` | `frame_skip=1` em vídeo de 10 frames processa exatamente 5 |
| Resize | idem | Resolução reportada reflete `target_width`/`target_height` |
| ROI | idem | Resolução final e `roi` no resultado refletem a região configurada |
| Metadados/timestamps | idem | `fps`/`duration_seconds` reais, tolerância de arredondamento do codec |
| Resoluções diferentes | idem | 128×96 processado corretamente |
| Vídeo curto (1 frame) / longo (100 frames) | idem | `frames_processed` correto nos dois extremos |
| Vídeo sem frames válidos | idem | `InferenceExecutionError` (reaproveita a validação de `VideoReader`) |
| Registry/troca de motor | `tests/inference/test_registry.py` | `basic_vision` é o default; `create_engine` resolve ambos os motores com `settings` |
| Pipeline completo | `tests/infrastructure/test_orchestrator_pipeline.py` | Continua passando com `BasicVisionEngine` real no lugar do `fake` |
| Regressão | Todos os 81 testes anteriores | Sem alteração de comportamento não intencional |

## Validação manual — stack real

Gerei um vídeo real de 30 frames (10fps, 64×48) e fiz upload real, disparando publicação real no Redis. Rodei `python -m worker.main` com `WORKER_INFERENCE_ENGINE=basic_vision`, `WORKER_FRAME_SKIP=2` e `WORKER_ENABLE_RESIZE=true` (`32×24`). Confirmado no log, por consulta ao Postgres/Redis, **e buscando o artefato de volta diretamente do R2 real** (via `boto3`, só para verificação — nunca no código do Worker):

```json
{"status": "processed", "detections": [], "frame_metadata": {"frame_count": 30, "width": 32, "height": 24, "fps": 10.0, "duration_seconds": 3.0}, "metadata": {"engine_name": "basic_vision", "engine_version": "1.0.0", "duration_ms": 15.0}, "frames_processed": 10, "frame_skip": 2, "roi": null}
```

`frames_processed=10` bate exatamente com o esperado (30 frames, skip=2 → índices 0,3,6,…,27). Resolução refletindo o resize real (32×24). `COMPLETED`/`progress=100`, Lock liberado, mensagem confirmada (`XPENDING=0`) — fluxo completo: `Redis → Download → VideoReader → FrameProvider → BasicVisionEngine → Upload → Cleanup → Unlock`.

## Preparação para a W7 (primeiro detector real)

Confirmado na prática: `BasicVisionEngine` já prova que um motor **real** (não fake) se encaixa no Pipeline sem alterar Pipeline, Orchestrator, Redis, Backend, R2 ou `video/`. A W7 repete exatamente esse encaixe:

1. `XInferenceEngine(InferenceEngine)` em `worker/inference/`, reaproveitando `video.VideoReader`/`FrameProvider`/`FrameIterator` e `inference.frame_ops` tal como `BasicVisionEngine` já faz.
2. `register_engine("x", XInferenceEngine)`.
3. `WORKER_INFERENCE_ENGINE=x`.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
