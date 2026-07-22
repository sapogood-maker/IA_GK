# SPRINT_W3_REPORT.md — Goalkeeper AI Worker: Pipeline de Processamento

> Escopo: construir o fluxo operacional completo do Worker. Sem OpenCV, sem YOLO, sem PyTorch, sem GPU, sem inferência, sem retry automático, sem heartbeat contínuo, sem scheduler, sem múltiplos Workers. A única parte falsa desta sprint é o processamento do vídeo em si — toda a estrutura ao redor é real.

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` (Seções 1-5), `AI_WORKER_ARCHITECTURE.md`, `DOMAIN_ARCHITECTURE.md`, os 9 ADRs, `ARCHITECTURE_REVIEW_W2.md` e `W2_1_REPORT.md` antes de implementar. Usei exatamente as 5 pastas reservadas na W2.1 (`orchestrator/`, `pipeline/`, `state/`, `workspace/`, `events/`), sem criar nenhuma pasta nova fora desse conjunto.

- **`worker/state/pipeline_state.py`** — `PipelineState`: `job_id`, `video_id`, `message_id`, `started_at`, `job`, `workspace_dir`, `download_path`, `artifact_path`, `lock_acquired`, `status`, `finished_at`, `errors`. Todo Stage recebe e devolve esta mesma estrutura.
- **`worker/workspace/manager.py`** — `WorkspaceManager.create`/`cleanup`, sempre via `tempfile.mkdtemp`, nunca caminho hardcoded.
- **`worker/events/events.py`** — `JobStarted`, `VideoDownloaded`, `ArtifactGenerated`, `UploadFinished`, `JobCompleted`, `JobFailed` — dataclasses simples + `emit()`, que hoje só loga (`video_id`/`job_id` sempre presentes, cumprindo a regra de Correlation ID). Preparado para futuramente alimentar métricas sem mudar quem chama `emit`.
- **`worker/pipeline/stages/`** — 11 Stages, cada um com uma única responsabilidade e a mesma assinatura `async def run(self, state) -> state`: `ReceiveJobStage`, `ValidateJobStage`, `AcquireLockStage`, `PrepareWorkspaceStage`, `DownloadVideoStage`, `FakeProcessingStage`, `GenerateArtifactStage`, `UploadArtifactStage`, `UpdateStatusStage`, `CleanupStage`, `ReleaseLockStage`.
- **`worker/orchestrator/orchestrator.py`** — `WorkerOrchestrator`: `process_job(message)` executa os 9 Stages de negócio dentro de um `try/except WorkerError`, e **sempre** roda `CleanupStage`/`ReleaseLockStage` num bloco `finally` (defensivos: só agem se `workspace_dir`/`lock_acquired` de fato existirem). `run_forever(shutdown_event)` consome do Redis (reaproveitando `ensure_consumer_group`/`read_next_job`/`ack_job` da W2) e chama `process_job` por mensagem — sem retry, sem heartbeat, sem scheduler.
- **`worker/infrastructure/storage/r2_client.py`** (novo — vazio desde a W2) — `download_to_path`/`upload_file`, HTTP simples via `httpx` contra a URL já assinada, nunca SDK do S3, nunca credencial mestra.
- **`worker/main.py`** — só cresceu o necessário para inicializar dependências (Redis client, `BackendClient` via `async with`) e delegar a `orchestrator.run_forever(event)`. Nenhuma lógica de Stage, Pipeline ou regra de negócio vive em `main.py`.

## Fluxo completo (confirmado na validação manual)

```
Redis (consumer group) → ReceiveJobStage → ValidateJobStage → AcquireLockStage
→ PrepareWorkspaceStage → DownloadVideoStage → FakeProcessingStage
→ GenerateArtifactStage → UploadArtifactStage → UpdateStatusStage
→ [finally] CleanupStage → ReleaseLockStage → ACK
```

Em caso de falha em qualquer Stage de negócio (`ReceiveJobStage` a `UpdateStatusStage`), o `orchestrator` captura `WorkerError`, marca `status="FAILED"`, emite `JobFailed`, e **ainda assim** executa Cleanup/ReleaseLock no `finally` — sem retry automático e sem rollback complexo, exatamente como pedido.

## Arquivos criados

`worker/state/pipeline_state.py`, `worker/workspace/manager.py`, `worker/events/events.py`, `worker/pipeline/stages/{__init__,base,receive_job,validate_job,acquire_lock,prepare_workspace,download_video,fake_processing,generate_artifact,upload_artifact,update_status,cleanup,release_lock}.py`, `worker/orchestrator/orchestrator.py`, `worker/infrastructure/storage/r2_client.py`.

Testes novos: `tests/test_workspace_manager.py`, `tests/test_events.py`, `tests/pipeline/{__init__,conftest,test_validate_job_stage,test_fake_processing_stage,test_generate_artifact_stage,test_receive_job_stage,test_download_video_stage,test_upload_artifact_stage,test_update_status_stage}.py`, `tests/infrastructure/{test_r2_client,test_pipeline_lock_stages,test_orchestrator_pipeline,test_main}.py`.

## Arquivos modificados

- `worker/core/exceptions.py` — `StorageError` e `PipelineError` (novas subclasses de `WorkerError`).
- `worker/infrastructure/backend_client/client.py` — `__aenter__`/`__aexit__` em `_BaseBackendClient` (fechamento automático de recursos, recomendação da `ARCHITECTURE_REVIEW_W2.md`).
- `worker/orchestrator/__init__.py`, `worker/pipeline/__init__.py`, `worker/state/__init__.py`, `worker/workspace/__init__.py`, `worker/events/__init__.py`, `worker/infrastructure/storage/__init__.py` — docstrings atualizadas (deixam de dizer "vazio").
- `worker/main.py` — inicializa Redis client + `BackendClient` e delega a `WorkerOrchestrator.run_forever`.
- `tests/test_main.py` **removido** — movido para `tests/infrastructure/test_main.py`, já que `run()` agora exige Redis real para criar o consumer group ao iniciar.

## Testes executados — 59/59 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Unitários | `tests/pipeline/*`, `tests/test_workspace_manager.py`, `tests/test_events.py` | Cada Stage isoladamente (HTTP mockado via `httpx.MockTransport` quando precisa do `BackendClient`), `WorkspaceManager` com sistema de arquivos real, eventos |
| Integração — Lock | `tests/infrastructure/test_pipeline_lock_stages.py` | `AcquireLockStage`/`ReleaseLockStage` contra Redis real |
| Integração — R2 | `tests/infrastructure/test_r2_client.py` | `download_to_path`/`upload_file` reais (mecânica HTTP), erro vira `StorageError` |
| Pipeline completo | `tests/infrastructure/test_orchestrator_pipeline.py` | 3 cenários com Redis real + Backend/R2 mockados (mesmo `MockTransport`): sucesso ponta a ponta, Job não encontrado, Lock já em uso — nos três, `workspace_dir`/`lock_acquired` ficam consistentes |
| Smoke test do processo | `tests/infrastructure/test_main.py` | `run()` inicia, entra no `run_forever`, encerra graciosamente — precisa de Redis real |

## Validação manual — stack real completo

Subi o stack real (Postgres + Redis + backend), criei club/goleiro/sessão reais, e desta vez fiz um **upload real de vídeo** (`POST /api/v1/videos/upload`, multipart, via um script Python com `httpx` — `curl` no Git Bash/Windows tem o mesmo bug de path já visto na Sprint 7) — isso subiu bytes de verdade ao R2 e publicou a mensagem real no Redis via `VideoUploadService`, sem nenhuma simulação manual.

Rodei `python -m worker.main` de verdade contra esse stack. Confirmado no log e por consulta direta ao Postgres/Redis após a execução:

1. **Redis** — consumiu a mensagem real publicada pelo upload.
2. **Lock** — adquirido; confirmado removido do Redis ao final (`GET lock:video:...` retornou vazio).
3. **Download** — `GET` real assinado contra o R2 configurado, 200 OK, 38 bytes (tamanho exato do vídeo fake enviado).
4. **Workspace** — criado via `tempfile`, log confirma o path em `%TEMP%`.
5. **Processamento Placeholder** — rodou (sem OpenCV/YOLO), artefato gerado em seguida.
6. **Upload** — `PUT` real assinado contra o R2, 200 OK com `ETag`/`x-amz-version-id` genuínos — artefato JSON realmente gravado no bucket.
7. **Status** — `PUT /jobs/{id}/status` real; consulta posterior confirmou `status=COMPLETED, progress=100.0, worker_id=worker-w3-e2e`.
8. **Cleanup** — log confirma `workspace_cleaned`.
9. **Unlock** — confirmado vazio no Redis.
10. **ACK** — `XPENDING` do consumer group retornou `0` (nenhuma mensagem pendente).

Tudo funcionando, de ponta a ponta, sem nenhuma simulação de infraestrutura — só o conteúdo do "vídeo" e o "processamento" são falsos.

## Limitações da W3

1. **Sem retry automático, sem heartbeat contínuo, sem scheduler** — deliberado, por instrução explícita. Uma falha transitória (ex.: R2 momentaneamente indisponível) marca o Job como `FAILED` na primeira tentativa.
2. **`AcquireLockStage` falhando marca o Job inteiro como `FAILED`** — nesta sprint não há uma noção de "tentar de novo mais tarde"; um vídeo já em processamento por outro Worker resulta em falha, não em reenfileiramento.
3. **Sobreposição de nome em `events/`** — já sinalizado no código: esta pasta guarda eventos internos operacionais (ciclo de vida do Job), mas a Constituição a reservava para o Event Registry (eventos técnicos de vídeo, W5). Os dois convivem por instrução explícita desta sprint; vale reavaliar nomes antes da W5.
4. **`AI_WORKER_CONSTITUTION.md` não foi resincronizada nesta sprint** — `orchestrator/`, `pipeline/`, `state/`, `workspace/`, `events/` deixaram de estar vazios, mas a Seção 12 (árvore do repositório) ainda os descreve como tal. Recomendo um novo ajuste pontual (mesmo espírito da W2.1) antes ou durante a W4.
5. **Workspace usa o diretório temporário do SO (`tempfile.mkdtemp`)**, não o `goalkeeper_ai_worker/workspace/` citado na árvore da Constituição — decisão deliberada para cumprir literalmente "sempre tempfile"; о diretório de dados de topo da Constituição segue sem uso real.
6. **Sem limite de tamanho/quota do workspace** — o vídeo real processado tinha 38 bytes; disciplina de espaço em disco sob carga real (Risco 7 da Constituição) continua em aberto.

## Preparação para a Sprint W4

A meta principal da W3 foi cumprida: **trocar `FakeProcessingStage` por uma Stage real de inferência (OpenCV/YOLO/PyTorch) não deve exigir alterar nenhuma outra parte do Pipeline.** `FakeProcessingStage.run(state)` recebe `state.download_path` (o vídeo já baixado) e devolve o mesmo `state` — uma Stage real de detecção só precisa ler esse mesmo caminho e popular algo em `state` (ou gerar um artefato mais rico em `GenerateArtifactStage`) para se encaixar exatamente onde `FakeProcessingStage` está hoje. `worker/gpu/`, `worker/registry/` e `worker/models/` seguem vazios, prontos para receber o Compute Backend e o Model Registry sem tocar em `orchestrator`, `pipeline/stages` (fora da própria Stage de inferência) ou `infrastructure/`.
