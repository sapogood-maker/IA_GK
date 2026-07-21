# SPRINT_W2_REPORT.md — Goalkeeper AI Worker: Comunicação

> Escopo: fazer o Worker falar de verdade com os três contratos públicos do Boundary Enforcement (Redis, Worker API do backend, Cloudflare R2) mais o Lock distribuído por vídeo. Sem pipeline, sem IA, sem alteração em `backend_fastapi/`. Plano revisado e aprovado antes da implementação (ver `C:\Users\P\.claude\plans\parallel-booping-taco.md`), incorporando 7 ajustes pedidos na revisão.

## O que foi implementado

### Configuração (`worker/config/settings.py`, estendido)

Novos campos, todos carregados do `.env`, nenhum hardcoded: `redis_url`, `consumer_group` (configurável via `WORKER_CONSUMER_GROUP` — ajuste 1), `backend_api_url`, `api_key`, `lock_ttl_seconds`, `protocol_version` (ajuste 6).

### `worker/contracts/` (novo)

Tipos que representam exclusivamente os contratos públicos do backend (ajuste 3) — nenhum importa `app/schemas/schemas.py`:
- `backend_api.py`: `JobDetails`, `JobStatusUpdate`, `PresignedUrl`, `ArtifactUploadUrlRequest`, `ArtifactUploadUrl`.
- `queue_message.py`: `JobMessage` (`job_id`, `video_id`, `message_id`) — formato da mensagem do stream Redis.

### `worker/infrastructure/` (novo — agrupa toda infraestrutura externa, ajuste 5)

- **`redis/client.py`**: `get_redis_client()`, singleton preguiçoso.
- **`redis/consumer.py`**: `ensure_consumer_group` (idempotente, ignora `BUSYGROUP`), `read_next_job` (`XREADGROUP`, bloqueante com timeout configurável), `ack_job` (`XACK`). Nome do grupo vem de `settings.consumer_group`.
- **`redis/lock.py`**: `acquire`/`release`/`renew` do Lock distribuído por vídeo (ADR-001/003) — `release`/`renew` usam script Lua atômico, só agem se o valor ainda pertencer ao `owner_id` que pediu. Renovação automática por heartbeat **não** entra nesta sprint — só a primitiva, testada isoladamente.
- **`backend_client/client.py`**: `_BaseBackendClient` (camada HTTP genérica — ajuste 2) com um único método `_request`, que injeta `X-Worker-Api-Key` e `X-Worker-Version` (ajuste 6) e traduz erro de rede em `BackendUnavailableError` / status ≥ 400 em `BackendRequestError`. `BackendClient` estende essa base e concentra os 4 métodos de endpoint hoje — estruturado para que `get_job`/`update_job_status` e `get_download_url`/`get_artifact_upload_url` possam futuramente virar mixins em `jobs.py`/`storage.py` sem tocar em `_request` (ajuste de organização final, nada disso foi criado agora).
- **`storage/`**: vazio, reservado — nesta sprint o canal R2 é validado só na geração das URLs assinadas (ajuste 4), não no download/upload real de bytes (isso é da W3).

### `worker/core/exceptions.py` (estendido)

Novas subclasses de `WorkerError`: `QueueConnectionError`, `BackendUnavailableError`, `BackendRequestError`.

### `worker/main.py`

**Inalterado** — decisão deliberada do plano: W2 prova que cada canal funciona isoladamente; a composição num laço real de consumo de Job (com retry/timeout/checkpoint) é da W3. Evita reescrever `main.py` duas vezes.

## Dependências novas

`redis==5.0.1`, `httpx==0.26.0` — mesmas versões já validadas no ambiente do backend (coincidência de escolha de dependência de terceiros, não compartilhamento de código/config).

## Testes automatizados — 25/25 passando

| Arquivo | O que valida |
|---|---|
| `tests/test_settings.py` (estendido) | Novos campos de config, obrigatoriedade de `backend_api_url`/`api_key` |
| `tests/infrastructure/test_redis_consumer.py` | Redis **real** e descartável: criação idempotente do grupo, leitura de mensagem publicada de verdade, `ACK` remove das pendências |
| `tests/infrastructure/test_lock.py` | Redis **real**: acquire/release/renew respeitando o dono correto |
| `tests/infrastructure/test_backend_client.py` | `httpx.MockTransport`: headers de autenticação/protocolo, path/verbo de cada endpoint, parsing para os tipos de `contracts/`, erro de rede vira `BackendUnavailableError`, status ≥ 400 vira `BackendRequestError` |

## Validação manual de ponta a ponta (contra o stack real)

Subi o stack real do backend (`docker compose up --build` — Postgres + Redis + backend), resetei o volume de Postgres (continha dados de teste de sprints anteriores desta mesma conversa) e criei via API real: usuário admin (bootstrap) → clube → goleiro → sessão → vídeo → job. Depois, com o Worker rodando fora do Docker (venv próprio), executei um script avulso que:

1. Cria o consumer group real (como o Worker faria ao iniciar).
2. Publica uma mensagem real no stream (`job_id`/`video_id` do job criado) e a lê de volta via `read_next_job`.
3. Chama `BackendClient.get_job` real, com a API Key real — recebeu `status=QUEUED` e o `video_id` correto.
4. Adquire e libera o Lock distribuído do vídeo real.
5. Chama `get_download_url` e `get_artifact_upload_url` reais — **as credenciais reais do Cloudflare R2 já estavam configuradas no `.env` do backend**, então as duas chamadas retornaram URLs assinadas de verdade (não um erro de configuração ausente, como eu esperava antes de checar).
6. Confirma (`ACK`) a mensagem — pendências voltam a zero.

Em nenhum momento chamei `update_job_status` contra o job real — só leitura e geração de URLs, que não alteram nada no Postgres. Ao final, removi o container de Redis de teste e derrubei o stack (`docker compose down`).

## Verificação de fronteira

`grep` recursivo em todo `goalkeeper_ai_worker/` por `backend_fastapi`/`from app.`/`import app.`: **zero ocorrências reais** (só as duas menções da própria regra, em docstring/README). Nenhuma alteração em `backend_fastapi/`.

## Fora do escopo desta sprint (W3+)

Download/upload real de bytes via as URLs assinadas; retry/timeout/checkpoint por Stage; renovação automática de Lock por heartbeat; qualquer laço de consumo orquestrado em `main.py`; Dockerfile do Worker; pipeline e IA.
