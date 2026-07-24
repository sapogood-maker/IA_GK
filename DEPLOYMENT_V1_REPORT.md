# DEPLOYMENT_V1_REPORT.md — Goalkeeper AI Worker: Docker Runtime (Deployment v1.0)

> Escopo: empacotar o Worker (MVP arquitetural W1–W27, congelado) para execução em Docker — Docker Desktop (Windows) hoje, Ubuntu Server + Docker Engine + NVIDIA Container Toolkit no futuro, sem nenhuma mudança de código. **Nenhum Analyzer, regra ou peça da arquitetura cognitiva foi alterado.** "Deployment v1.0" é a versão deste esquema de empacotamento, distinta de `worker.__version__` (0.1.0) e de `WORKER_PROTOCOL_VERSION`.

## Arquitetura final

O MVP (`worker/analyzers/`, `worker/domain/`, `worker/inference/`, `worker/orchestrator/`, `worker/pipeline/`) permanece **byte-a-byte idêntico** ao estado da Sprint W27. Esta sprint só adiciona:

- `deployment/docker/` — Dockerfile, docker-compose.yml, entrypoint.sh, .env.example, .dockerignore, README.md (os entregáveis pedidos).
- Três arquivos novos, pequenos e isolados, **fora** da árvore `analyzers/`/`domain/`/`inference/`/`orchestrator`/`pipeline` — puramente operacionais, nunca chamados pelo Pipeline/Orchestrator/Analyzer em runtime:
  - `worker/infrastructure/redis/health.py` — `redis_is_reachable(settings)`, PING descartável.
  - `worker/wait_for_redis.py` — CLI chamado pelo `entrypoint.sh`, aguarda o Redis antes do Worker iniciar.
  - `worker/healthcheck.py` — CLI chamado pela instrução `HEALTHCHECK` do Dockerfile.
- Duas extensões aditivas e não-invasivas a módulos de infraestrutura pré-cognitiva (não Analyzers): `worker/config/settings.py` (dois campos novos, `log_dir`/`startup_wait_timeout_seconds`) e `worker/observability/logging_setup.py` (log em arquivo rotacionado, opcional, aditivo ao `StreamHandler` existente).
- Uma correção em `requirements.txt` (achado real desta sprint, ver abaixo).

## Deliverables

```
goalkeeper_ai_worker/
├── .dockerignore                      # copia funcional (raiz do build context)
└── deployment/
    └── docker/
        ├── Dockerfile                  # multi-stage: builder (deps) + runtime (não-root)
        ├── docker-compose.yml          # só o serviço `worker`
        ├── .dockerignore                # copia do entregável (ver nota dentro do arquivo)
        ├── .env.example                 # template enxuto para Docker
        ├── entrypoint.sh                 # aguarda Redis, depois exec do processo principal
        └── README.md                     # como rodar (Docker Desktop) e migrar (Ubuntu+GPU)
```

## Dockerfile — decisões

- **Multi-stage build**: `builder` instala dependências num virtualenv (`/opt/venv`); `runtime` só copia o virtualenv pronto — a imagem final não carrega `build-essential`/cache de pip.
- **CPU-only por padrão, sem exigir GPU**: `torch==2.13.0+cpu`/`torchvision==0.28.0+cpu` instalados explicitamente do índice oficial do PyTorch (`https://download.pytorch.org/whl/cpu`) **antes** de `requirements.txt` — sem isso, a resolução de dependências do `ultralytics` (que só exige `torch>=1.8.0`) puxaria o wheel CUDA padrão do PyPI, dezenas de vezes maior e inútil sem runtime NVIDIA. Versões idênticas às já validadas no ambiente de teste do próprio projeto.
- **Usuário não-root**: `worker` (uid/gid 1000), `--shell /usr/sbin/nologin`. Diretórios de volume (`/app/logs`, `/app/weights`) criados e com dono trocado **antes** do `USER worker` — um volume Docker monta com o dono definido no momento do build/primeira montagem, então a ordem importa.
- **Nenhuma credencial na imagem**: só código é copiado (`worker/`, `pyproject.toml`, `entrypoint.sh`). `.dockerignore` exclui `.env`/`.env.*` explicitamente; toda configuração real chega via `env_file` do docker-compose, em runtime.
- **Health Check e `CMD`**: ver seções dedicadas abaixo.

## Achado real desta sprint 1: `ultralytics` conflita com `opencv-python-headless`

Ao validar o build limpo (nunca feito antes desta sprint — todo o desenvolvimento W1-W27 rodou num venv local já preexistente, nunca reconstruído do zero a partir de `requirements.txt`), a imagem falhou em `import cv2` com `ImportError: libxcb.so.1` — uma dependência X11 que a imagem deliberadamente não instala (`opencv-python-headless`, escolhido desde a W5 exatamente para não depender de GUI/X11).

**Causa raiz**: `ultralytics==8.4.104` declara `opencv-python` (variante COM GUI) como dependência própria obrigatória, independentemente do que `requirements.txt` já satisfaça. As duas distribuições (`opencv-python`/`opencv-python-headless`) instalam o MESMO pacote `cv2/` — a que for instalada por último sobrescreve fisicamente os arquivos da outra. Não é um erro de resolução do pip; é um conflito real e conhecido do ecossistema ultralytics/opencv.

**Correção**: após `pip install -r requirements.txt`, reinstalar `opencv-python-headless==4.10.0.84` com `--force-reinstall --no-deps`, garantindo deterministicamente que seus arquivos fiquem por cima. Documentado no `Dockerfile` (stage `builder`).

## Achado real desta sprint 2: `lap` faltando em `requirements.txt`

O container falhou ao importar `worker.orchestrator.orchestrator` com `ModuleNotFoundError: No module named 'lap'` — `lap` (Linear Assignment Problem solver, usado por `ultralytics.trackers.byte_tracker.BYTETracker`, consumido pelo Worker desde a W9) nunca esteve listado em `requirements.txt`. O ambiente de desenvolvimento local usado em TODAS as sprints anteriores já tinha `lap` instalado (por algum motivo não seguido/registrado), mascarando essa lacuna real de dependência — só a construção de uma imagem verdadeiramente limpa a partir de `requirements.txt` a expôs.

**Correção**: `lap==0.5.13` adicionado a `requirements.txt` (versão idêntica à já validada no ambiente de teste do projeto). Corrigido via `build-essential` já presente no stage `builder` (compila a extensão nativa do `lap` sem esforço extra).

Ambos os achados confirmam o valor de validar contra um build genuinamente limpo — nenhum dos dois seria descoberto sem tentar `docker build` de verdade.

## Health Check

`worker/healthcheck.py` (script standalone, chamado por `HEALTHCHECK` no Dockerfile a cada 30s) define "saudável" como **"capaz de fazer trabalho útil agora"**: as duas dependências externas críticas do Worker precisam estar alcançáveis — Redis (`PING`) e a Worker API do backend (`GET /health`, endpoint público sem autenticação). Deliberadamente **não** verifica estado interno do laço de consumo (`WorkerOrchestrator.run_forever`, congelado desde a W3) — evita reportar "unhealthy" durante o processamento legítimo de um Job longo, sem exigir NENHUMA mudança no Orchestrator/Pipeline.

## Graceful Shutdown

Já implementado desde a Sprint W1 (`worker/core/lifecycle.py`, `install_shutdown_handlers`/`wait_for_shutdown`) — nenhuma mudança de código nesta sprint. Dois detalhes de empacotamento tornam isso efetivo dentro do container:

1. `entrypoint.sh` usa `exec "$@"` — o processo Python vira PID 1 do container, então `SIGTERM` do `docker stop` chega direto ao handler do Worker, em vez de ser absorvido pelo shell do entrypoint.
2. `stop_grace_period: 120s` no `docker-compose.yml` — o laço de consumo só verifica o sinal de encerramento **entre** Jobs (nunca no meio de um), então um vídeo longo pode legitimamente levar mais que o `stop_grace_period` padrão do Docker (10s).

## Aguardar Redis / Reconexão — decisão explícita

- **Aguardar antes de iniciar**: `entrypoint.sh` chama `python -m worker.wait_for_redis` (novo), que faz `PING` a cada 2s até `WORKER_STARTUP_WAIT_TIMEOUT_SECONDS` (padrão 60s) ou sucesso, então `exec`-a o processo principal. Timeout esgotado → container falha ao iniciar de forma visível (exit code 1), nunca sobe travado silenciosamente.
- **Reconexão após o startup — decisão explícita, sem código novo**: não foi adicionado retry/reconexão dentro do `WorkerOrchestrator`/`redis.asyncio` (ambos fora do escopo desta sprint, congelados desde W2/W3/W9). A resiliência vem de duas camadas já existentes: (1) o connection pool do `redis.asyncio` cria conexões novas sob demanda — uma queda momentânea não deixa o cliente "quebrado"; (2) se o Redis cair durante uma leitura bloqueada, a exceção não é capturada hoje e o processo encerra — e `restart: unless-stopped` reinicia o container, que passa de novo pelo `wait_for_redis`. "Deixe cair, deixe o Docker reiniciar" é documentado como o padrão de resiliência ESCOLHIDO desta versão, não uma lacuna escondida.
- **Cloudflare R2**: cada download/upload é uma requisição HTTP nova via URL assinada (`httpx`, sem conexão persistente) — não há "reconexão" a fazer; já tratado pelos Stages existentes desde a W3.

## Volumes

| Volume | Monta em | Papel |
|---|---|---|
| `goalkeeper_worker_logs` | `/app/logs` | Log rotacionado (`WORKER_LOG_DIR=/app/logs`, 10MB × 5) — aditivo ao `docker logs`, nunca no lugar. |
| `goalkeeper_worker_weights` | `/app/weights` | Pesos do YOLO — baixados automaticamente pela Ultralytics no primeiro uso, reaproveitados em restarts. |

## Preparação para GPU NVIDIA (Ubuntu, futuro)

Documentado em detalhe em `deployment/docker/README.md`. Resumo: só TRÊS coisas mudam entre CPU (hoje) e GPU (futuro) — a base image (`python:3.11-slim` → uma imagem CUDA), o pacote torch (índice CPU → índice CUDA correspondente), e o bloco `deploy.resources.reservations.devices` do `docker-compose.yml` (já presente, comentado). **Nenhuma linha de `worker/` muda** — `YOLODetector`/`ultralytics` já detectam e usam CUDA automaticamente via `torch.cuda.is_available()`; a Analyzer API (W13-W27) nunca soube nem precisa saber se roda em CPU ou GPU.

## Validação manual — build e execução reais

Build limpo (`docker build`), sem cache de nenhum ambiente Python pré-existente:

```
docker build -f deployment/docker/Dockerfile -t goalkeeper-ai-worker:0.1.0 .
```

Confirmado (após corrigir os dois achados acima): `import cv2` (headless, sem `libxcb`), `from ultralytics import YOLO`, `from ultralytics.trackers.byte_tracker import BYTETracker`, `import worker.orchestrator.orchestrator` — todos OK. `torch.__version__` = `2.13.0+cpu`, `torch.cuda.is_available()` = `False` (esperado, CPU-only).

**Cadeia completa real, com o stack do backend rodando** (`docker compose up -d` em `backend_fastapi/`) e o Worker subindo via `deployment/docker/docker-compose.yml` apontando para `host.docker.internal`:

1. Container iniciou, `entrypoint.sh` aguardou e confirmou Redis alcançável (`redis_reachable_worker_can_start`).
2. `WorkerOrchestrator` carregou, baixou `yolo11n.pt` automaticamente no volume `/app/weights` (5.4MB, ~0.2s).
3. `docker compose ps` reportou `healthy` após o `start_period`.
4. Upload real de vídeo via a API do backend → Job publicado no Redis → Worker consumiu, processou com os **15 Analyzers** ativos, fez upload do artefato no R2, atualizou o status → `JobCompleted`.
5. Artefato confirmado no R2: `analysis_statistics.results_count == 15`, `goalkeeper_analysis_report` presente e coerente (`coaching`/`performance` = `insufficient_information`, mesmo comportamento real de detecção já observado nas validações W24-W27), `worker_version` = `0.1.0`, `generated_at` um timestamp real.
6. Volumes confirmados persistentes: `/app/logs/worker.log` com conteúdo real; `/app/weights/yolo11n.pt` presente.
7. **Health Check**: `docker inspect` reportou `Status: healthy`.
8. **Graceful shutdown**: `docker stop` → `docker inspect .State.ExitCode` = `0` (não `137`/SIGKILL), `FinishedAt` ~2.1s após o sinal de parada ser recebido pelo processo — dentro do esperado para o laço `block_ms=2000`. (A latência adicional observada no round-trip do comando `docker stop` em si, no Docker Desktop/WSL2, é overhead do CLI/daemon, não do Worker — o processo já havia saído graciosamente muito antes.)
9. **Negative path — Redis inalcançável**: container apontado para uma porta Redis inexistente, com `WORKER_STARTUP_WAIT_TIMEOUT_SECONDS=5`, retornou exit code `1` após tentar e logar `redis_unreachable_after_timeout` — comportamento correto de falha rápida e visível.

Stack derrubado ao final (`docker compose down` nos dois lados); volumes nomeados preservados (dados reais, não descartados).

## Testes — 544/544 passando

Além da suíte completa existente (534 do estado pós-W27), 10 testes novos, todos usando um Redis real descartável (mesma disciplina de `tests/infrastructure/`, nunca mockado) e HTTP mockado via `httpx.MockTransport` (mesma disciplina de `test_backend_client.py`):

| Arquivo | O que valida |
|---|---|
| `tests/infrastructure/test_redis_health.py` | `redis_is_reachable()` — `True` contra Redis real, `False` contra porta inalcançável |
| `tests/infrastructure/test_wait_for_redis.py` | `_wait_until_reachable()`/`main()` — sucesso imediato, timeout esgotado, exit codes 0/1 |
| `tests/infrastructure/test_healthcheck.py` | `_is_healthy()` — saudável (Redis+backend OK), não-saudável (Redis inalcançável / backend inalcançável / backend retorna 5xx) |
| `tests/test_settings.py` | `startup_wait_timeout_seconds`/`log_dir` — defaults e configurabilidade |
| `tests/test_logging_setup.py` | `configure_logging` sem `WORKER_LOG_DIR` (comportamento inalterado, só `StreamHandler`) e com `WORKER_LOG_DIR` (arquivo rotacionado criado, `StreamHandler` preservado) |

Todos os 534 testes anteriores (W1-W27) continuam passando sem nenhuma alteração de comportamento.

## Limitações conhecidas (documentadas honestamente, não escondidas)

- **Reconexão automática com Redis** é alcançada via `restart: unless-stopped` + connection pool do `redis.asyncio`, não via retry/backoff explícito dentro do `WorkerOrchestrator`. Documentado como decisão desta versão, não uma lacuna.
- **Warning cosmético da Ultralytics**: `user config directory '/home/worker/.config/Ultralytics' is not writable, using '/tmp/Ultralytics'` aparece nos logs mesmo com o diretório genuinamente gravável pelo usuário `worker` (confirmado manualmente) — aparenta ser uma checagem de escrita incorreta/prematura da própria biblioteca Ultralytics, não do Worker. Sem efeito funcional (fallback automático para `/tmp`, que funciona); não investigado mais a fundo por ser cosmético e fora do escopo desta sprint.
- **`stop_grace_period: 120s`** é um valor padrão razoável, não calibrado a nenhuma duração real de vídeo em produção — ajustar conforme os vídeos processados forem tipicamente mais longos.
- **GPU NVIDIA não testada nesta sprint** (não exigida) — a preparação é estrutural/documentada, não validada contra hardware real.

## Roadmap

Deployment v1.0 (Docker, CPU) está completo e validado. Próximos passos possíveis, sem sprint definida: migração real para Ubuntu Server (validar `extra_hosts`/rede compartilhada em produção), habilitação de GPU NVIDIA quando houver hardware disponível, e os itens pós-MVP já registrados em `AI_WORKER_CONSTITUTION.md` (Seção 16).
