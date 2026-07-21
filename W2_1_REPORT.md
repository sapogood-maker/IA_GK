# W2_1_REPORT.md — Sprint W2.1: Alinhamento Arquitetural

> Sprint exclusivamente de consolidação, sem pipeline, sem IA, sem alteração em `backend_fastapi/`. Objetivo: fechar os 4 itens "Obrigatórios" do `ARCHITECTURE_REVIEW_W2.md` antes de iniciar a Sprint W3.

## O que foi feito

### 1. `AI_WORKER_CONSTITUTION.md` sincronizada com a implementação real

- Seção 1 (tabela de módulos): `contracts`, `infrastructure/redis`, `infrastructure/backend_client`, `infrastructure/storage`, `workspace` e `core` passam a existir oficialmente, com a mesma responsabilidade que já tinham no código. `queue`/`lock`/`backend_client`/`storage` deixam de aparecer como pastas irmãs soltas de `worker/` — agora refletem que vivem sob `infrastructure/`.
- Seção 12 (árvore do repositório): reescrita para mostrar `contracts/`, `infrastructure/{redis,backend_client,storage}`, `core/`, e marcada explicitamente quais pastas estão vazias e até qual sprint (`orchestrator/`→W3, `gpu/`/`registry/`/`models/`→W4, `tracking/`/`metrics/`/`events/`/`artifacts/`→W5). `pyproject.toml`, `.env.example`, `.gitignore`, `README.md` e `tests/` (já implementado, não mais "reservado") também entraram na árvore.
- Nota de abertura do documento atualizada: deixa de dizer "revisão final antes da primeira linha de código" (defasado desde a W1) e passa a se declarar um documento vivo, registrando que a W2.1 foi quem sincronizou Seção 1/12 com o código real.

### 2. Cinco pacotes vazios criados (só `__init__.py` + docstring, nenhuma lógica)

`worker/orchestrator/`, `worker/pipeline/`, `worker/state/`, `worker/workspace/`, `worker/events/` — cada docstring explica a responsabilidade futura do módulo e até qual sprint ele permanece vazio, mesmo padrão já usado em `models/`/`infrastructure/storage/` desde a W1/W2.

### 3. `QueueConnectionError` corrigida

Antes: definida em `worker/core/exceptions.py`, nunca levantada — falhas reais de conexão com o Redis vazavam como `redis.exceptions.*` cru. Agora: `ensure_consumer_group`, `read_next_job`, `ack_job` (`infrastructure/redis/consumer.py`) e `acquire`/`release`/`renew` (`infrastructure/redis/lock.py`) capturam `redis.exceptions.RedisError` e relançam como `QueueConnectionError` — exceto o caso `BUSYGROUP` em `ensure_consumer_group`, que continua sendo um no-op esperado (idempotência), não um erro.

**Testado com falha de conexão real**, não mockada: `tests/infrastructure/test_redis_connection_errors.py` aponta um cliente para uma porta sem nada escutando (`localhost:1`) e confirma que as 4 operações levantam `QueueConnectionError`.

## Testes — 29/29 passando

25 testes anteriores (W1+W2) + 4 novos de `test_redis_connection_errors.py`. Suíte rodada com Redis de teste real (container descartável) após o Docker Desktop precisar ser reiniciado no meio da sprint (ambiente, não código).

## Verificação de fronteira

`grep` recursivo confirmou, mais uma vez, zero import cruzado com `backend_fastapi/` em todo `goalkeeper_ai_worker/`.

## Confirmação: arquitetura e implementação sincronizadas

Sim. Após esta sprint, `AI_WORKER_CONSTITUTION.md` §1/§12 descrevem exatamente os módulos que existem hoje em `goalkeeper_ai_worker/worker/` — nenhuma pasta real ficou de fora do documento, e nenhuma pasta do documento afirma existir sem existir de fato (as vazias estão marcadas como tal, com a sprint em que deixam de estar vazias).

---

## Organização do histórico — proposta para sua aprovação

Nenhum commit foi feito ainda para `goalkeeper_ai_worker/` nem para os documentos de arquitetura — confirmei isso na revisão anterior e continua verdadeiro. Preciso ser transparente sobre uma limitação real antes de propor a sequência: **como nada foi commitado incrementalmente, alguns arquivos já foram sobrescritos ou removidos entre uma sprint e outra** (ex.: `worker/queue/` da W1 não existe mais — virou `worker/infrastructure/redis/` na W2; `worker/config/settings.py` da W1 já tem os campos da W2 misturados no mesmo arquivo). Não tenho como reconstruir o estado exato de disco ao final de cada sprint sem risco de erro.

Por isso, a sequência abaixo agrupa por **assunto/entrega**, não por um recorte perfeito de "arquivo tal como estava exatamente ao final daquela sprint":

| # | Commit | Conteúdo |
|---|---|---|
| 1 | `docs: arquitetura oficial do Goalkeeper AI Worker` | `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md` (estado atual — já reflete monorepo/ADR-009/Boundary Enforcement/sincronização da W2.1, não há como separar isso em commits anteriores sem histórico prévio) |
| 2 | `feat(worker): Sprint W1 - fundacao do Worker` | `goalkeeper_ai_worker/{README.md, .env.example, requirements.txt, pyproject.toml, .gitignore}`, `worker/{__init__.py, main.py, config/, core/, observability/, models/}`, `tests/{__init__.py, conftest.py, test_lifecycle.py, test_logging_setup.py, test_main.py, test_settings.py}` |
| 3 | `feat(worker): Sprint W2 - comunicacao (Redis, Backend API, R2, Lock)` | `worker/contracts/`, `worker/infrastructure/`, `SPRINT_W2_REPORT.md`, `tests/infrastructure/{__init__.py, conftest.py, test_backend_client.py, test_lock.py, test_redis_consumer.py}` |
| 4 | `docs: revisao arquitetural pos-W2` | `ARCHITECTURE_REVIEW_W2.md` |
| 5 | `feat(worker): Sprint W2.1 - alinhamento arquitetural` | `worker/{orchestrator,pipeline,state,workspace,events}/__init__.py`, `tests/infrastructure/test_redis_connection_errors.py`, `W2_1_REPORT.md` |

## Decisão final: commit único, sem reconstrução de histórico

Você escolheu a opção de commit único consolidado, explicitamente rejeitando qualquer tentativa de reconstruir um histórico incremental que nunca existiu de fato.

**O histórico oficial do Goalkeeper AI Worker começa no commit `f651f90` — `feat(worker): bootstrap Goalkeeper AI Worker` — por decisão deliberada, não por limitação técnica escondida.** Esse commit representa o primeiro estado oficialmente validado do projeto: fundação (W1), camada de comunicação (W2), sincronização arquitetural (W2.1), Architecture Review aprovada, Boundary Enforcement validado, 29/29 testes passando. Está marcado com a tag anotada `worker-v0.1.0-bootstrap`.

Não existe, e não foi criado artificialmente, nenhum commit anterior "representando" a W1 ou a W2 isoladamente — a granularidade real daquelas sprints só existe nesta conversa e nos relatórios (`SPRINT_W2_REPORT.md`, `ARCHITECTURE_REVIEW_W2.md`, este documento), não no grafo do Git. A partir deste marco, toda nova sprint (a começar pela W3) passa a gerar commits próprios, incrementais, no fluxo normal.
