# Goalkeeper AI Worker — Deployment v1.0 (Docker Runtime)

Empacotamento do Worker (MVP arquitetural W1–W27, congelado — nenhum Analyzer, regra ou arquitetura cognitiva foi alterado nesta sprint) para execução em Docker. Roda hoje em CPU no Docker Desktop (Windows); a mesma imagem/compose migra para Ubuntu Server + Docker Engine sem nenhuma mudança de código, e está preparada (mas não exige) para GPU NVIDIA nesse momento futuro.

"Deployment v1.0" é a versão deste **esquema de empacotamento** — distinta de `worker.__version__` (versão do software, hoje `0.1.0`) e de `WORKER_PROTOCOL_VERSION` (versão do contrato REST). Mesmo princípio de não confundir versões já usado desde a Sprint W2/W27.

## Arquivos deste diretório

| Arquivo | Papel |
|---|---|
| `Dockerfile` | Build multi-stage (builder + runtime), usuário não-root, Health Check, `CMD`. |
| `docker-compose.yml` | Sobe o serviço `worker` (só ele — Redis/backend não são definidos aqui, ver "Topologia" abaixo). |
| `entrypoint.sh` | Aguarda o Redis ficar alcançável (`worker.wait_for_redis`) antes de `exec`-ar `python -m worker.main`. |
| `.env.example` | Template enxuto das variáveis para Docker — copie para `.env` (mesmo diretório) antes de subir. |
| `.dockerignore` | Cópia do `.dockerignore` real (que vive na raiz do repositório do Worker — ver nota dentro do arquivo). |

## Pré-requisitos (Docker Desktop, Windows)

- Docker Desktop instalado e rodando (WSL2 backend recomendado).
- O stack do backend (`backend_fastapi/docker-compose.yml`) já rodando, com Redis e a Worker API publicados em `localhost:6379`/`localhost:8001` (as portas padrão desse compose).

## Topologia — Worker é um deploy independente

Por Boundary Enforcement (`AI_WORKER_CONSTITUTION.md`), o Worker nunca compartilha compose file/infraestrutura com `backend_fastapi/`. Este `docker-compose.yml` só define o serviço `worker`; ele se conecta ao Redis e à Worker API do backend via configuração (`.env`), não via um serviço Docker compartilhado. Dois modos são suportados:

### Modo 1 — Teste rápido no Docker Desktop (`host.docker.internal`)

O padrão do `.env.example` deste diretório. `host.docker.internal` é resolvido nativamente pelo Docker Desktop (Windows/Mac) para o IP do host — nenhuma configuração extra necessária:

```env
WORKER_REDIS_URL=redis://host.docker.internal:6379/0
WORKER_BACKEND_API_URL=http://host.docker.internal:8001
```

No Ubuntu + Docker Engine, `host.docker.internal` **não** é resolvido por padrão — por isso o `docker-compose.yml` já inclui:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Essa única linha é o que faz o **mesmo** `.env`/`docker-compose.yml` funcionar sem alteração nos dois sistemas operacionais.

### Modo 2 — Rede Docker compartilhada (recomendado para produção)

Se o backend também roda em containers no mesmo host, anexar o Worker à rede do compose do backend evita depender de portas publicadas no host:

```yaml
# override local (docker-compose.override.yml), não versionado
services:
  worker:
    networks:
      - backend_net
networks:
  backend_net:
    external: true
    name: backend_fastapi_default   # nome real da rede do compose do backend
```

E no `.env`, usar os nomes de serviço do backend em vez de `host.docker.internal`:

```env
WORKER_REDIS_URL=redis://redis:6379/0
WORKER_BACKEND_API_URL=http://backend:8001
```

## Subindo no Docker Desktop

```powershell
cd goalkeeper_ai_worker\deployment\docker
copy .env.example .env
# edite .env: pelo menos WORKER_API_KEY deve bater com o WORKER_API_KEY do backend

docker compose build
docker compose up -d

docker compose logs -f worker
docker compose ps          # STATUS deve chegar a "healthy" apos o start_period
```

Parar (graceful shutdown real, não `kill -9`):

```powershell
docker compose stop worker     # envia SIGTERM, aguarda ate stop_grace_period (120s) antes de SIGKILL
docker compose down            # idem, e remove o container (volumes preservados)
```

## Health Check

`worker/healthcheck.py` (chamado pela instrução `HEALTHCHECK` do Dockerfile a cada 30s) define "saudável" como **"capaz de fazer trabalho útil agora"**: as duas dependências externas críticas do Worker precisam estar alcançáveis —

1. Redis (a fila de Jobs).
2. A Worker API do backend (`GET /health`, endpoint público, sem autenticação).

Deliberadamente **não** verifica o estado interno do laço de consumo (`WorkerOrchestrator.run_forever`) — nenhuma mudança foi feita lá para evitar reportar "unhealthy" durante o processamento legítimo de um Job longo. `docker compose ps`/`docker inspect --format='{{.State.Health.Status}}' goalkeeper_ai_worker` mostram o status atual.

## Graceful Shutdown

Já implementado desde a Sprint W1 (`worker/core/lifecycle.py`) — `SIGTERM`/`SIGINT` sinalizam um `asyncio.Event`, verificado entre Jobs pelo laço de consumo (`WorkerOrchestrator.run_forever`, Sprint W3). Dois detalhes tornam isso efetivo dentro do container:

- `entrypoint.sh` usa `exec "$@"` — o processo Python vira o PID 1 do container, então o `SIGTERM` do `docker stop` chega direto no handler do Worker, em vez de ser absorvido pelo shell do entrypoint.
- `stop_grace_period: 120s` no `docker-compose.yml` — como o Worker só verifica o sinal de encerramento **entre** Jobs (nunca no meio de um), um vídeo longo pode legitimamente levar mais que o `stop_grace_period` padrão do Docker (10s). Ajustar esse valor para cima se os vídeos processados forem tipicamente mais longos que ~2 minutos.

## Aguardar o Redis / Reconexão automática

- **Aguardar antes de iniciar**: `entrypoint.sh` chama `python -m worker.wait_for_redis`, que faz `PING` no Redis a cada 2s até `WORKER_STARTUP_WAIT_TIMEOUT_SECONDS` (padrão 60s) ou sucesso. Se o timeout esgotar, o container falha ao iniciar de forma visível (`docker compose logs`), em vez de o Worker subir e travar silenciosamente sem fila.
- **Reconexão após o startup**: **decisão explícita desta sprint** — não foi adicionado nenhum laço de retry/reconexão dentro do `WorkerOrchestrator`/`worker/infrastructure/redis/client.py` (ambos congelados desde a W2/W9, fora do escopo desta sprint). Em vez disso, a resiliência vem de duas camadas já existentes:
  1. O `redis.asyncio.Redis` (client.py, Sprint W2) usa um connection pool que cria uma conexão nova sob demanda a cada comando — uma queda momentânea do Redis não deixa o cliente "permanentemente quebrado".
  2. Se o Redis cair enquanto o laço de consumo está bloqueado numa leitura (`XREADGROUP ... BLOCK`), a exceção não é capturada hoje e o processo encerra — e `restart: unless-stopped` (docker-compose.yml) reinicia o container automaticamente, que passa de novo pelo `wait_for_redis` do entrypoint. Esse é o comportamento assumido (documentado, não escondido) desta versão: "deixe cair, deixe o Docker reiniciar" é um padrão de resiliência valido e comum em containers — não seria necessário reimplementar retry manual dentro do código do Worker para atingir o mesmo resultado prático.
- **Cloudflare R2**: cada download/upload é uma requisição HTTP nova via URL assinada (`httpx`, sem conexão persistente) — não há "reconexão" a fazer; uma falha de rede em uma chamada gera um erro tratado pelo Stage correspondente (`DownloadVideoStage`/`UploadArtifactStage`, já existentes desde a W3), sem exigir mudança nesta sprint.

## Volumes

| Volume | Monta em | Conteúdo |
|---|---|---|
| `goalkeeper_worker_logs` | `/app/logs` | Logs em arquivo rotacionado (`WORKER_LOG_DIR=/app/logs`), 10MB × 5 arquivos. Sem esta variável, os logs só vão para `docker compose logs` (stdout/stderr). |
| `goalkeeper_worker_weights` | `/app/weights` | Pesos do modelo YOLO (`WORKER_MODEL_PATH=weights/yolo11n.pt`) — baixados automaticamente pela Ultralytics no primeiro uso (precisa de acesso à internet nesse momento) e reaproveitados em restarts seguintes via este volume, sem novo download. |

Nenhuma credencial é armazenada na imagem nem nestes volumes — toda configuração (incluindo `WORKER_API_KEY`) vem exclusivamente do `.env` montado via `env_file` em runtime.

## Migração futura: Ubuntu Server + Docker Engine + NVIDIA Container Toolkit

A mesma imagem/`docker-compose.yml` funciona em Ubuntu sem nenhuma mudança de código. Passos:

1. **Instalar Docker Engine + Docker Compose plugin** no Ubuntu Server (ver documentação oficial da Docker — `apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin`).
2. **Copiar o repositório** (ou só `goalkeeper_ai_worker/`) para o servidor.
3. **`extra_hosts: host.docker.internal:host-gateway`** já está no `docker-compose.yml` — nenhuma mudança necessária para o Modo 1 continuar funcionando; para produção, preferir o Modo 2 (rede Docker compartilhada) descrito acima.
4. **`docker compose build && docker compose up -d`** — build normal, CPU, idêntico ao Windows.

### Habilitando GPU NVIDIA (quando desejado, não obrigatório)

1. Instalar o **NVIDIA Container Toolkit** no host Ubuntu (driver NVIDIA + `nvidia-container-toolkit`, `nvidia-ctk runtime configure --runtime=docker`, `systemctl restart docker`) — passo feito no HOST, fora deste repositório.
2. Trocar a base image do `Dockerfile` de `python:3.11-slim` para uma imagem CUDA (ex.: `nvidia/cuda:12.x-cudnn-runtime-ubuntu22.04` + instalar Python 3.11 nela, ou uma imagem `pytorch/pytorch:*-cuda*-cudnn*-runtime` já pronta).
3. Trocar a instalação de `torch`/`torchvision` do stage `builder` do índice CPU (`--index-url https://download.pytorch.org/whl/cpu`) para o índice CUDA correspondente à versão instalada no host (ex.: `--index-url https://download.pytorch.org/whl/cu121`).
4. Descomentar o bloco `deploy.resources.reservations.devices` (driver `nvidia`) no `docker-compose.yml`.
5. **Nenhuma mudança em `worker/`** — `YOLODetector`/`ultralytics` já detectam e usam CUDA automaticamente quando disponível (`torch.cuda.is_available()`), sem nenhum código condicional no Worker. A Analyzer API (W13-W27) nunca soube nem precisa saber se roda em CPU ou GPU — ela só consome `FootballWorld`.

Esses são os ÚNICOS três pontos que mudam entre CPU (hoje) e GPU (futuro): base image, pacote torch, e o bloco `deploy` do compose — nunca o código Python do Worker.

## Variáveis de ambiente

Ver `.env.example` (este diretório) para a lista enxuta de variáveis para rodar em Docker, e `../../.env.example` (raiz do repositório do Worker) para a lista completa de todos os parâmetros/limiares dos 15 Analyzers (W13-W27) — qualquer variável de lá também pode ser adicionada ao `.env` deste diretório, sem nenhuma mudança no `Dockerfile`/`docker-compose.yml`.

## Troubleshooting

| Sintoma | Causa provável | O que checar |
|---|---|---|
| Container reinicia em loop, log mostra `redis_unreachable_after_timeout` | Redis não alcançável no endereço configurado | `WORKER_REDIS_URL` no `.env`; se usando `host.docker.internal`, confirme que o Redis do backend está publicado na porta esperada no host |
| `docker compose ps` nunca mostra `healthy` | Backend ou Redis inalcançável, ou ambos ainda subindo | `docker compose logs worker`; confirmar `WORKER_BACKEND_API_URL`/`WORKER_REDIS_URL`; aguardar o `start_period` (40s) |
| `401` nos logs ao processar um Job | `WORKER_API_KEY` não bate com o `WORKER_API_KEY` do backend | Confirmar que os dois `.env` (Worker e backend) têm o MESMO valor |
| Job trava/timeout ao processar vídeo grande, container reiniciado no meio | `stop_grace_period` menor que o tempo real de processamento | Aumentar `stop_grace_period` no `docker-compose.yml` |
