# SPRINT7_REPORT.md — Preparação da Infraestrutura do AI Worker

> Escopo: exclusivamente infraestrutura de preparação. Nenhuma linha de YOLO, OpenCV, ByteTrack, DeepSORT, modelos de ML, inferência, processamento de vídeo ou análise de frames foi criada. Nenhum repositório `ai_worker`, Docker de Worker, pipeline ou endpoint de submissão de resultados de IA foi criado. Análise prévia de `AI_WORKER_ARCHITECTURE.md`, `DOMAIN_ARCHITECTURE.md`, `SPRINT5_REPORT.md` e `SPRINT6_REPORT.md` confirmou compatibilidade antes de qualquer alteração.

## Arquitetura implementada

### 1. Service Account do Worker (autenticação separada)

- `app/core/worker_auth.py`: dependência `require_worker_api_key`, valida o header `X-Worker-Api-Key` contra `Settings.worker_api_key`. **Fail-closed**: sem a variável configurada, nenhuma chave é aceita.
- **Separação completa e testada**: um router novo (`app/api/v1/worker.py`) usa exclusivamente essa dependência — nenhum endpoint dele aceita `Depends(get_current_user)` (JWT), e nenhum router humano aceita a API Key. Confirmado por 3 testes automatizados dedicados (JWT rejeitado no Worker, API Key rejeitada em endpoint humano, e vice-versa).

### 2. Endpoints do Worker

Todos sob `/api/v1/worker`, exigindo `X-Worker-Api-Key`:
- `GET /jobs/{job_id}` — detalhes do job.
- `PUT /jobs/{job_id}/status` — progresso, conclusão e falha consolidados num único endpoint (evita 3 endpoints quase idênticos); marca `started_at`/`completed_at` automaticamente.
- `POST /jobs/{job_id}/download-url` — URL assinada de leitura do vídeo do job.
- `POST /jobs/{job_id}/artifacts/upload-url` — URL assinada de escrita para um artefato, com `r2_key` já escopado (`artifacts/{video_id}/{job_id}/{filename}`).

### 3. URLs assinadas

- `R2Service.generate_presigned_upload_url` (novo — só existia a de leitura antes desta sprint).
- Expiração **configurável e separada** por direção: `WORKER_DOWNLOAD_URL_EXPIRATION_SECONDS` / `WORKER_UPLOAD_URL_EXPIRATION_SECONDS` (`Settings`, padrão 3600s cada).
- Documentado em `AI_WORKER_ARCHITECTURE.md` (seção "Sprint 7").

### 4. Redis (infraestrutura, sem consumer)

- `app/core/queue.py`: cliente Redis assíncrono (`redis.asyncio`), stream `processing_jobs`, função `publish_processing_job`. Nenhum consumer/consumer group — o futuro Worker cria o seu próprio ao iniciar.
- `docker-compose.yml`: serviço `redis` (imagem `redis:7-alpine`, healthcheck, volume próprio).

### 5. Publicação de jobs

`VideoUploadService.upload_video` chama `publish_processing_job(job.id, video.id)` logo após criar o `ProcessingJob`. Falha de publicação é só logada — não interrompe o upload (o vídeo já está salvo no R2 e o registro no banco existe; a fila é suplementar até existir um Worker consumindo-a).

### 6. Monitoramento da fila (sem Prometheus)

- Logging estruturado (chave=valor) em `app/core/queue.py`: sucesso (`job_id`, `video_id`, `message_id`, `duration_ms`) e falha de publicação.
- `GET /api/v1/queue/health` — endpoint **humano** (`SYSTEM_ADMIN`, JWT — não usa a API Key do Worker), retorna conectividade e tamanho do stream. Confirmado refletindo o estado real do Redis num teste de ponta a ponta (upload real → stream com 1 mensagem).

## ⚠️ Achado real e importante durante a validação

Ao testar o upload real contra o Docker rodando de verdade, os logs estruturados do item 6 **não apareciam em lugar nenhum**. Investigando, descobri que **o projeto nunca chamou `logging.basicConfig()`** — o nível padrão do logger raiz do Python (`WARNING`) descartava silenciosamente **todo `logger.info(...)` da aplicação inteira**, desde o início do projeto (isso afeta não só os logs novos da fila, mas também os logs já existentes em `video_upload_service.py` e `r2.py`, nunca visíveis em nenhuma sprint anterior). Corrigido com um `logging.basicConfig(level=logging.INFO, ...)` em `app/main.py`. Confirmado depois da correção: os logs estruturados de publicação passaram a aparecer corretamente no `docker logs`.

## Arquivos alterados

### Backend

| Arquivo | Mudança |
|---|---|
| `app/main.py` | `logging.basicConfig` (correção do achado acima); registra os 2 novos routers do Worker |
| `app/core/config.py` | `worker_api_key`, `redis_url`, `worker_download_url_expiration_seconds`, `worker_upload_url_expiration_seconds` |
| `app/core/r2.py` | `generate_presigned_upload_url` (novo) |
| `app/core/worker_auth.py` **(novo)** | Autenticação por API Key, separada do JWT |
| `app/core/queue.py` **(novo)** | Cliente Redis, publisher, diagnóstico da fila |
| `app/schemas/schemas.py` | Schemas do Worker (`WorkerJobStatusUpdate`, `PresignedUrlResponse`, `ArtifactUploadUrlRequest/Response`, `QueueHealthResponse`) |
| `app/api/v1/worker.py` **(novo)** | 4 endpoints do Worker (API Key) + `GET /queue/health` (JWT/admin, router separado) |
| `app/services/video_upload_service.py` | Publica na fila após criar o `ProcessingJob` |
| `docker-compose.yml` | Serviço `redis`; `REDIS_URL`/`WORKER_API_KEY` no backend |
| `requirements.txt` | `redis==5.0.1` |
| `.env.example` | Novas variáveis documentadas |
| `backend_fastapi/tests/conftest.py` | Redis de teste, helper `worker_auth_header` |
| `backend_fastapi/tests/test_worker_auth.py`, `test_worker_endpoints.py`, `test_queue.py` **(novos)** | 18 testes novos |

### Documentação

- `AI_WORKER_ARCHITECTURE.md`: seção "Sprint 7" com o que passou de design para implementação real (autenticação, endpoints, URLs assinadas, fila).
- `SPRINT7_REPORT.md` (este arquivo).

Nenhuma migration nova foi necessária — nenhum campo/tabela do banco mudou (a infraestrutura do Worker usa exclusivamente colunas que já existiam desde as Sprints 1-5: `ProcessingJob.status/progress/error_message/worker_id/started_at/completed_at`, `Video.r2_key`).

## Testes executados

| Verificação | Resultado |
|---|---|
| `ruff check` | 0 achados |
| `python -m py_compile` em todo o backend | Sem erros |
| `pytest` (18 testes novos + 30 anteriores) | **48/48 passaram** |
| `flutter analyze`/`test`/`build` | Inalterado desde a Sprint 6 (nenhum arquivo de frontend tocado nesta sprint) |
| `docker compose up --build` (Postgres + **Redis** + backend) | 3 containers `healthy`; migrações em `005` (nenhuma nova) |
| Upload real de vídeo → fila | Confirmado: `stream_length` do Redis foi de 0 para 1 após um upload real contra o R2 configurado |
| Separação de autenticação (ao vivo, via `curl`/Python) | JWT rejeitado no Worker (401); API Key rejeitada em endpoint humano (401); API Key correta funciona no Worker (404 esperado, pois o job de teste não existia — prova que passou da autenticação) |

## Decisões tomadas

1. **Um único endpoint de status** (`PUT .../status`) em vez de 3 separados ("atualizar progresso", "finalizar", "registrar falha") — evita duplicar validação quase idêntica; os 3 comportamentos do pedido são cobertos pelos valores possíveis de `status`.
2. **`GET /queue/health` fica num router humano separado** (`admin_router`, no mesmo arquivo `worker.py` por tratar do mesmo subsistema), não no router do Worker — é uma ferramenta para administradores humanos monitorarem a fila, não algo que o Worker chama.
3. **API Key única e compartilhada**, não uma por máquina/worker — suficiente para o estágio atual (nenhum Worker existe ainda); documentado como evolução futura se o parque de máquinas crescer.
4. **Não criado endpoint de submissão de resultados** (Analysis/Event/Metric) — não estava na lista de exemplos do pedido, e depende de inferência real existir primeiro. Ver pendência abaixo.

## Pendências restantes

1. Endpoint(s) para o Worker submeter os resultados estruturados da análise (criar `Analysis` + `Event`/`Metric` associados) — não existe ainda.
2. API Key única compartilhada, sem revogação por máquina individual.
3. CORS permissivo (`*` + credenciais) — pendência já registrada na Sprint 6, ainda não resolvida (depende dos domínios de produção).
4. Repositório do Worker, pipeline, inferência — deliberadamente fora do escopo de todas as sprints até aqui.

## Pergunta final: o Worker conseguiria consumir a infraestrutura sem alterar o backend?

**Parcialmente sim, mas não completamente.**

**O que já funciona, sem precisar de nenhuma mudança no backend:**
- Autenticar-se (API Key).
- Descobrir um job novo (consumir o stream `processing_jobs`, criando seu próprio consumer group — isso é responsabilidade do Worker, não do backend).
- Buscar detalhes do job.
- Obter uma URL assinada e baixar o vídeo original.
- Reportar progresso ao longo do processamento.
- Obter uma URL assinada e subir artefatos (thumbnails, clipes, etc.).
- Marcar o job como concluído ou como falho.

**O que ainda exigiria uma mudança no backend:** não existe nenhum endpoint para o Worker **submeter o resultado estruturado da análise** — ou seja, criar a linha em `Analysis` (que hoje não tem nenhum ponto de criação em lugar nenhum do sistema) e as linhas correspondentes em `Event`/`Metric`. O Worker conseguiria processar o vídeo inteiro, baixar, atualizar progresso e até subir artefatos — mas na hora de registrar "detectei 18 eventos, aqui estão eles", bateria numa parede, porque esse endpoint não foi construído nesta sprint (deliberadamente — não estava na lista de exemplos pedida, e depende de haver inferência real produzindo esses dados).

Isso deve ser o primeiro item da próxima sprint de infraestrutura antes de o Worker ser realmente iniciado, ou construído junto com a primeira versão do Worker que efetivamente gerar resultados.
