# SPRINT_W5_REPORT.md — Goalkeeper AI Worker: Infraestrutura de Leitura de Vídeo

> Escopo: construir `worker/video/`, reutilizável por todo motor de inferência futuro. Ainda sem detecção, inferência, YOLO ou OpenCV como mecanismo de IA — OpenCV foi usado exclusivamente como biblioteca de leitura (`cv2.VideoCapture`). Nenhuma linha de `cv2.dnn`, GPU, CUDA ou ROCm foi escrita.

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` (Seção 15 — que já definia esta sprint), `AI_WORKER_ARCHITECTURE.md`, os 9 ADRs, `SPRINT_W4_REPORT.md` e `SPRINT_W4_1_REPORT.md` antes de implementar.

Criei `worker/video/` como módulo **irmão** de `worker/inference/`, nunca dentro dele — `VideoReader` é infraestrutura, `inference/` continua sendo só IA:

| Arquivo | Responsabilidade |
|---|---|
| `exceptions.py` | `VideoError` → `VideoOpenError`, `InvalidVideoError`, `FrameReadError` (todas de `WorkerError`) |
| `types.py` | `VideoProperties` (fps/width/height/frame_count/duration_seconds) — lidas uma única vez na abertura |
| `metadata.py` | `FrameMetadata` — posição do frame (`frame_index`/`timestamp_seconds`/`position_seconds`) + propriedades do vídeo de origem |
| `frame.py` | `Frame` — a imagem (`numpy.ndarray`, BGR) + `FrameMetadata` |
| `reader.py` | `VideoReader` — abre/fecha (`cv2.VideoCapture`), valida (rejeita frame_count/fps/dimensões inválidos), expõe `VideoProperties`; suporta `with VideoReader(path) as reader:` |
| `provider.py` | `FrameProvider` — leitura sequencial (`read_next()`), distingue fim normal do vídeo (retorna `None`) de falha real de leitura antes do fim esperado (`FrameReadError`) |
| `iterator.py` | `FrameIterator` — protocolo padrão de iterador Python (`__iter__`/`__next__`, `StopIteration` no fim) |

**`FakeInferenceEngine` reescrita** (`inference/fake_engine.py`) para consumir `VideoReader`/`FrameProvider`/`FrameIterator` em vez de ler bytes crus — conta frames de verdade e lê fps/dimensões/duração reais do vídeo, sem nenhuma análise de conteúdo. `inference/types.py`'s `FrameMetadata` ganhou o campo `duration_seconds` (não existia na W4, necessário para carregar o dado real que passou a existir). O contrato `InferenceEngine.process(state) -> state` (`inference/base.py`) **não mudou** — `inference/` continua conhecendo só `FrameProvider`/`FrameIterator`/`VideoReader`, nunca decide nada sobre eles além de consumi-los.

**Sobre o exemplo de JSON da especificação** (`{"frames": 1234, "fps": 30, "duration": 41.2, "engine": "fake"}`): optei por manter a estrutura tipada já existente (`InferenceResult.to_dict()`, Seção "Evitar dicionários soltos" da W4) em vez de voltar a um dicionário plano — os mesmos dados existem, só aninhados (`frame_metadata.frame_count`/`fps`/`duration_seconds`, `metadata.engine_name`). Sinalizo essa escolha explicitamente, já que diverge do exemplo literal.

## Fluxo atualizado

```
Redis → ReceiveJobStage → ValidateJobStage → AcquireLockStage → PrepareWorkspaceStage
→ DownloadVideoStage → InferenceStage
    → FakeInferenceEngine.process(state)
        → VideoReader(state.download_path) [abre, valida]
        → FrameProvider(reader)
        → for frame in FrameIterator(provider): conta frames
        → gera InferenceResult com frame_count/fps/width/height/duration REAIS
        → salva artifact.json
→ UploadArtifactStage → UpdateStatusStage → [finally] CleanupStage → ReleaseLockStage → ACK
```

## Arquivos criados

`worker/video/{__init__,exceptions,types,metadata,frame,reader,provider,iterator}.py`.

Testes novos: `tests/video/{__init__,test_reader,test_provider,test_iterator,test_exceptions}.py`.

## Arquivos alterados

- `worker/inference/fake_engine.py` — reescrita para consumir `worker.video` (versão do motor bump para `0.2.0`, refletindo a mudança real de comportamento).
- `worker/inference/types.py` — `FrameMetadata` ganhou `duration_seconds`; `to_dict()` atualizado.
- `requirements.txt` — `opencv-python-headless==4.9.0.80`, `numpy==1.26.4`.
- `tests/conftest.py` — fixtures `real_video_path`/`corrupted_video_path`/`missing_video_path` (vídeo real gerado com OpenCV, nunca mockado), compartilhadas entre `tests/video/` e `tests/inference/`.
- `tests/inference/test_fake_engine.py` — reescrito para usar vídeo real em vez de bytes crus.
- `tests/infrastructure/test_orchestrator_pipeline.py` — o mock de download do R2 agora serve bytes de um vídeo real (`real_video_path.read_bytes()`), já que `FakeInferenceEngine` abre de verdade o arquivo baixado; asserção nova de `frame_count`.

**Nenhuma mudança em `DownloadVideoStage`, `WorkspaceManager`, `BackendClient`, `infrastructure/redis/*`** — confirmei empiricamente que o OpenCV abre arquivos sem extensão (o nome usado por `DownloadVideoStage`, `input_video`) via detecção de conteúdo, então nenhum ajuste foi necessário ali.

## Testes — 81/81 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Abertura de vídeo | `tests/video/test_reader.py` | Propriedades reais lidas corretamente; erro para arquivo inexistente e corrompido; context manager abre/fecha; `properties`/`capture` recusam uso antes de `open()`; `close()` idempotente |
| Leitura de frames | `tests/video/test_provider.py` | Frames lidos em ordem com índice correto; contagem bate com o metadado; `FrameMetadata` carrega fps/dimensões/duração reais; `None` no fim do vídeo |
| Iterator | `tests/video/test_iterator.py` | Protocolo padrão do Python, para de forma limpa (`StopIteration`) |
| Exceções | `tests/video/test_exceptions.py` | Toda a hierarquia deriva de `WorkerError` |
| Integração com `FakeInferenceEngine` | `tests/inference/test_fake_engine.py` | Lê vídeo real de ponta a ponta, artefato reflete `frame_count`/`fps`/dimensões reais; vídeo corrompido vira `InferenceExecutionError` |
| Pipeline completo | `tests/infrastructure/test_orchestrator_pipeline.py` | Os 3 cenários da W3/W4 continuam passando, agora com vídeo real no mock do R2 |
| Regressão | Todos os 65 testes anteriores | Continuam passando sem alteração de comportamento não intencional |

## Validação manual — stack real

Gerei um vídeo real (15 frames, 10fps, OpenCV) e fiz upload real (`POST /api/v1/videos/upload`, via `httpx` — `curl`/Git Bash no Windows continua com o bug de path já visto desde a Sprint 7), disparando publicação real no Redis. Rodei `python -m worker.main` de verdade. Confirmado no log e por consulta direta ao Postgres/Redis:

`Redis (mensagem real consumida) → Download (200 real do R2) → VideoReader abre o vídeo real → FrameIterator conta os frames → FakeInferenceEngine gera o artefato com dados reais → Upload (PUT real, 200) → Status (COMPLETED, progress=100) → Cleanup → Unlock (confirmado vazio no Redis) → ACK (XPENDING=0)`.

Tudo funcionando, ponta a ponta, com um vídeo genuíno sendo aberto e lido pela primeira vez nesta sprint.

## Preparação para a W6 (`OpenCVInferenceEngine`)

A meta da W5 foi cumprida: criar `OpenCVInferenceEngine` na W6 deverá exigir só:

1. Escrever `worker/inference/opencv_engine.py`, implementando `InferenceEngine.process(state)` — internamente, abrir `state.download_path` com `VideoReader`, iterar com `FrameProvider`/`FrameIterator` (exatamente como `FakeInferenceEngine` já faz) e, a cada `Frame`, rodar a primeira operação real de visão computacional (ex.: um detector simples, ainda sem modelo treinado próprio).
2. `register_engine("opencv", OpenCVInferenceEngine)` em `inference/registry.py`.
3. `WORKER_INFERENCE_ENGINE=opencv` no `.env`.

**Nenhuma mudança esperada em** `worker/video/`, `Pipeline`, `Orchestrator`, `Workspace`, `Redis`, `Backend` ou `R2` — `worker/video/` já expõe exatamente o que um motor real vai precisar (frames reais, metadados reais), e o contrato `InferenceEngine` já está estável desde a W4.

## Pendência sinalizada (não corrigida agora)

`AI_WORKER_CONSTITUTION.md` segue sem resincronizar desde a W4.1 — precisará de uma nova mini-sprint de alinhamento (mesmo espírito da W2.1/W4.1) registrando `worker/video/` como módulo oficial (Seção 1/12) e resolvendo a questão que a Seção 15 deixou em aberto ("onde VideoReader mora") — já respondida na prática: em `worker/video/`, módulo irmão de `inference/`, não dentro dele.
