# SPRINT_W4_REPORT.md — Goalkeeper AI Worker: Arquitetura da Camada de Inferência

> Escopo: criar a arquitetura definitiva da camada de inferência, plugável desde o primeiro dia. Nenhuma linha de OpenCV, YOLO, MediaPipe, OpenPose, OCR, GPU, ROCm, CUDA, TensorRT foi escrita. Sem multi-GPU, scheduler, retry ou heartbeat contínuo. O Worker continua funcionando exatamente como ao final da W3 — a única mudança de comportamento é a forma do artefato JSON gerado.

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` (Seção 6 — Plugin Registry), `AI_WORKER_ARCHITECTURE.md`, `DOMAIN_ARCHITECTURE.md`, os 9 ADRs, `ARCHITECTURE_REVIEW_W2.md`, `W2_1_REPORT.md` e `SPRINT_W3_REPORT.md` antes de implementar.

Criei o módulo `worker/inference/` como **único lugar onde código de visão computacional pode existir** — Pipeline, Orchestrator, Workspace, `infrastructure/{redis,backend_client,storage}` nunca importam nada de dentro dele além do contrato:

| Arquivo | Responsabilidade |
|---|---|
| `base.py` | `InferenceEngine` (ABC) — o contrato único: `name`, `version`, `async def process(state) -> state` |
| `types.py` | `Detection`, `FrameMetadata`, `InferenceMetadata`, `InferenceResult` — nenhum dicionário solto |
| `exceptions.py` | `InferenceError` → `EngineInitializationError`, `InferenceExecutionError` (todas de `WorkerError`) |
| `fake_engine.py` | `FakeInferenceEngine` — implementação placeholder |
| `registry.py` | `register_engine`/`get_engine_class`/`available_engines` — mapa nome → classe |
| `engine.py` | `create_engine(nome)` — resolve e instancia a partir de `WorkerSettings.inference_engine`, nunca hardcoded |

**Decisão importante, decorrente da própria especificação da sprint:** `FakeInferenceEngine` não só processa como também **gera e salva o artefato JSON** — absorvendo a responsabilidade que antes pertencia à `GenerateArtifactStage` (W3). A instrução desta sprint listava explicitamente "Salvar um JSON" entre as responsabilidades do motor, então removi `GenerateArtifactStage` e `FakeProcessingStage` do Pipeline (arquivos deletados, não deixados como código morto) — cada motor real futuro (OpenCV, YOLO) decide sozinho o formato do seu próprio resultado e como persisti-lo, o que faz sentido já que resultados de motores diferentes são estruturalmente diferentes.

`InferenceStage` (`worker/pipeline/stages/inference.py`) substitui as duas: **7 linhas**, só chama `self._engine.process(state)`. Nenhuma Stage conhece OpenCV/YOLO/PyTorch — só esse contrato.

## Fluxo atualizado

```
Redis → ReceiveJobStage → ValidateJobStage → AcquireLockStage → PrepareWorkspaceStage
→ DownloadVideoStage → InferenceStage (chama engine.process) → UploadArtifactStage
→ UpdateStatusStage → [finally] CleanupStage → ReleaseLockStage → ACK
```

`WorkerOrchestrator` agora constrói o motor ativo uma única vez, na inicialização: `InferenceStage(create_engine(settings.inference_engine))` — trocar `WORKER_INFERENCE_ENGINE=fake` para `WORKER_INFERENCE_ENGINE=opencv` (quando existir) muda qual motor é instanciado, sem tocar em nenhuma linha do `orchestrator.py`.

## Arquivos criados

`worker/inference/{__init__,base,types,exceptions,fake_engine,registry,engine}.py`, `worker/pipeline/stages/inference.py`.

Testes novos: `tests/inference/{__init__,test_fake_engine,test_registry}.py`, `tests/pipeline/test_inference_stage.py`.

## Arquivos alterados

- `worker/state/pipeline_state.py` — novo campo `inference_result: InferenceResult | None`.
- `worker/config/settings.py` — novo campo `inference_engine` (`WORKER_INFERENCE_ENGINE`, default `"fake"`).
- `worker/orchestrator/orchestrator.py` — `InferenceStage`/`create_engine` no lugar de `FakeProcessingStage`/`GenerateArtifactStage`.
- `.env.example` — nova variável documentada.
- `tests/test_settings.py` — cobertura do novo campo.
- `tests/infrastructure/test_orchestrator_pipeline.py` — asserção do JSON ajustada ao novo formato (`status`/`detections`/`frame_metadata`/`metadata.engine_name`), em vez do antigo `{"status", "worker", "version"}`.

## Arquivos removidos

`worker/pipeline/stages/fake_processing.py`, `worker/pipeline/stages/generate_artifact.py` e seus testes (`tests/pipeline/test_fake_processing_stage.py`, `tests/pipeline/test_generate_artifact_stage.py`) — responsabilidade absorvida por `FakeInferenceEngine`/`InferenceStage`, sem deixar código morto para trás.

## Testes — 65/65 passando

| Categoria | Onde | O que valida |
|---|---|---|
| `FakeInferenceEngine` | `tests/inference/test_fake_engine.py` | Lê o vídeo baixado, escreve o artefato JSON com o formato de `InferenceResult`, levanta `InferenceExecutionError` se o vídeo não existir |
| `InferenceStage` | `tests/pipeline/test_inference_stage.py` | Delega inteiramente ao motor recebido (motor de teste, sem nenhuma lógica própria na Stage) |
| Registry + troca de motor | `tests/inference/test_registry.py` | `create_engine("fake")` resolve `FakeInferenceEngine`; nome desconhecido levanta `EngineInitializationError`; **registrar um segundo motor de teste e resolvê-lo via `create_engine` prova a troca sem tocar em Pipeline/Orchestrator** |
| Settings | `tests/test_settings.py` | `WORKER_INFERENCE_ENGINE` configurável, default `"fake"` |
| Pipeline completo | `tests/infrastructure/test_orchestrator_pipeline.py` | Os 3 cenários da W3 (sucesso, Job não encontrado, Lock em uso) continuam passando com `InferenceStage` no lugar das duas Stages antigas |
| Regressão | Todos os 59 testes da W1-W3 | Continuam passando sem nenhuma alteração de comportamento esperado |

## Validação manual — stack real

Reaproveitei o fluxo já validado na W3 (upload real via `httpx` — `curl` no Git Bash/Windows continua com o bug de path da Sprint 7 — sessão de treino real, vídeo real enviado ao R2, Job real publicado no Redis) e rodei `python -m worker.main` explicitamente com `WORKER_INFERENCE_ENGINE=fake`. Confirmado no log e por consulta direta ao Postgres/Redis:

`Redis → Lock → Download (200 real do R2) → InferenceStage → FakeInferenceEngine (lê o vídeo, gera e salva o JSON) → Upload (PUT real, 200) → Status (COMPLETED, progress=100) → Cleanup → Unlock (confirmado vazio no Redis) → ACK (XPENDING=0)`.

Tudo funcionando, ponta a ponta, igual à W3 — a única diferença observável é a ausência do evento `ArtifactGenerated` (que existia quando `GenerateArtifactStage` era uma Stage separada; agora a geração do artefato é interna ao motor) e o novo formato do JSON salvo no R2.

## Preparação para OpenCV

Criar `OpenCVInferenceEngine(InferenceEngine)` em `worker/inference/opencv_engine.py`, implementando `process(state)`: abrir `state.download_path` com `cv2.VideoCapture`, popular `FrameMetadata` (dimensões/fps/contagem de frames reais, hoje zerados), gerar `Detection`s reais, montar `InferenceResult` e salvar como artefato — exatamente o que `FakeInferenceEngine` já faz, só trocando "gerar um resultado simples" por "gerar um resultado real". Depois, `register_engine("opencv", OpenCVInferenceEngine)` em `registry.py` e `WORKER_INFERENCE_ENGINE=opencv` no `.env`. Nenhuma mudança em `Pipeline`, `Orchestrator`, `Workspace`, `Redis`, `Backend` ou `R2`.

## Preparação para YOLO

Mesma mecânica: `YOLOInferenceEngine(InferenceEngine)`, populando `Detection.label`/`confidence`/`frame_index` com as classes/caixas reais detectadas. Como `Detection` já é um tipo próprio (não um dicionário solto), o formato do artefato não muda estruturalmente ao trocar de OpenCV puro para YOLO — só o conteúdo das detecções fica mais rico. `PoseInferenceEngine`/`MultiModelInferenceEngine` seguem o mesmo caminho; o `Registry` já foi desenhado para isso desde o primeiro commit desta sprint (`tests/inference/test_registry.py::test_swapping_the_active_engine_requires_only_registration_and_config` prova isso registrando um motor de teste, sem nenhum código de produção sabendo que ele existe).

## Pendências sinalizadas (herdadas da W3, ainda não fechadas)

`AI_WORKER_CONSTITUTION.md` segue sem resincronização desde a W2.1 — agora também precisaria registrar `inference/` como módulo oficial. Recomendo uma nova mini-sprint de alinhamento (mesmo espírito da W2.1) antes de introduzir o primeiro motor real, para a Constituição não acumular mais divergência.
