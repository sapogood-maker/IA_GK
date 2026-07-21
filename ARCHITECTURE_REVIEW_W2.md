# ARCHITECTURE_REVIEW_W2.md — Goalkeeper AI Worker

> Revisão arquitetural pós-Sprint W2, antes do início da Sprint W3. Nenhum código foi escrito ou alterado para produzir este documento — apenas leitura e análise de `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, `DOMAIN_ARCHITECTURE.md`, todos os 9 ADRs, a seção Boundary Enforcement, e a implementação completa em `goalkeeper_ai_worker/` (config, core, observability, contracts, infrastructure, tests, README, pyproject, requirements, `.env.example`).

---

# 1. Resumo Executivo

**Nota geral: 8.5/10.** A arquitetura implementada nas Sprints W1 e W2 é sólida, coerente com os princípios congelados, e não contém nenhuma violação de Boundary Enforcement. O ponto que mais pesa contra a nota é que a própria `AI_WORKER_CONSTITUTION.md` ficou desatualizada em relação a decisões estruturais tomadas (e aprovadas por você) durante o planejamento da W2 — a documentação, que este projeto trata como fonte de verdade, não reflete mais 100% o código real.

**Pontos fortes:**
- Zero import cruzado com `backend_fastapi/` — confirmado por grep nesta própria revisão, não apenas relatado nos sprints anteriores.
- Separação de camadas limpa: `_BaseBackendClient` (HTTP genérico) vs. `BackendClient` (endpoints) é exatamente o tipo de preparação para crescimento que não custa nada agora e evita refatoração depois.
- Nenhuma abstração de IA/Pipeline/Orchestrator foi construída prematuramente — `models/`, `storage/`, `gpu/`, `registry/` seguem vazios ou inexistentes, exatamente onde deveriam estar nesta altura do roadmap.
- Contratos (`worker/contracts/`) cumprem literalmente a exigência de Boundary Enforcement de nunca importar `app/schemas/schemas.py` do backend, mesmo duplicando campos.
- O Lock distribuído (`acquire`/`release`/`renew`) usa script Lua atômico para evitar a corrida clássica de "liberar o lock de outro dono" — implementação correta do ADR-001/003, já validada com Redis real.

**Pontos fracos:**
- `AI_WORKER_CONSTITUTION.md` §1 e §12 descrevem uma árvore de módulos (`queue/`, `lock/`, `backend_client/`, `storage/` como irmãos diretos de `worker/`) que **não é mais a árvore real** desde que `infrastructure/` foi criado na W2. Isso nunca foi corrigido no documento.
- `contracts/` e `core/` — dois módulos reais e já em uso — não existem em nenhuma lista oficial da Constituição.
- Uma exceção (`QueueConnectionError`) foi definida mas nunca é levantada em lugar nenhum — a promessa de "todo erro do Worker herda de `WorkerError`" ainda não é verdade para falhas de conexão Redis.
- **Todo o diretório `goalkeeper_ai_worker/` está sem nenhum commit** — dois sprints inteiros de trabalho existem apenas na working tree.

---

# 2. Conformidade

| Item da Constituição | Situação real | Veredito |
|---|---|---|
| §1 Tabela de módulos (`orchestrator`, `pipeline`, `queue`, `lock`, `backend_client`, `storage`, `gpu`, `registry`, `state`, `submission`) | `queue`→`infrastructure/redis/consumer.py`, `lock`→`infrastructure/redis/lock.py`, `backend_client`→`infrastructure/backend_client/`, `storage`→`infrastructure/storage/` (vazio). `orchestrator`, `pipeline`, `gpu`, `registry`, `state`, `submission` **ainda não existem** (esperado — são W3+) | ⚠️ Divergente na nomenclatura/agrupamento, não no princípio |
| §2 Ordem dos Stages | Nenhum Stage foi implementado ainda (W3) | Não aplicável ainda — nenhuma violação |
| §3 Correlation ID (`video_id`+`job_id` em todo log) | Nenhuma linha de log de processamento de Job existe ainda (não há laço de consumo real); os logs existentes (startup, criação de grupo) corretamente não carregam `video_id`/`job_id` porque não são sobre um Job específico | ✓ Consistente — regra ainda não testável, mas não violada |
| §4 Lock — TTL + renovação por heartbeat | `acquire`/`release`/`renew` existem e testados; renovação automática por heartbeat **não existe** (heartbeat em si também não existe) | ✓ Conforme o roadmap revisado (heartbeat não é W1-W5) |
| §6 Plugin Registry único | Nenhum Plugin/Registry existe ainda (W4+) | Não aplicável ainda |
| §9 Contrato Backend↔Worker | `BackendClient` implementa exatamente os 4 endpoints hoje existentes no backend, com os nomes de campo corretos (`ProcessingJobResponse`, `WorkerJobStatusUpdate`, etc., replicados em `contracts/backend_api.py`) | ✓ Fiel, campo a campo |
| §12 Árvore do repositório | Diverge: `infrastructure/` (com `redis/`, `backend_client/`, `storage/`) e `contracts/` não aparecem na árvore oficial; `core/` também não | ❌ Documento desatualizado |
| §13 Roadmap | W1 ✓, W2 ✓ conforme descrito | ✓ |
| Boundary Enforcement (ver Seção 3 abaixo) | Auditado à parte | ✓ Sem violações |

**Conclusão da conformidade:** a arquitetura **de princípios** (independência, camadas, ausência de lógica de negócio, contratos explícitos) está 100% respeitada. A arquitetura **de nomenclatura/estrutura de pastas** documentada tem 3 divergências reais (`infrastructure/`, `contracts/`, `core/`) que nunca foram retro-incorporadas à Constituição. Isso não é um erro de implementação — as 3 mudanças foram decisões suas, tomadas e aprovadas durante o planejamento da W2 (ver `parallel-booping-taco.md`) — mas ficaram registradas só no plano de sprint, não no documento constitucional.

---

# 3. Boundary Enforcement — Auditoria Completa

| Proibição | Verificado | Resultado |
|---|---|---|
| Imports cruzados | `grep -rn "backend_fastapi\|from app\.\|import app\."` em todo `goalkeeper_ai_worker/**/*.py` | **Zero ocorrências reais** (só a própria regra documentada em `worker/__init__.py`) |
| Compartilhamento de Models | Nenhum arquivo do Worker importa SQLAlchemy nem qualquer `models.py` do backend | ✓ Limpo |
| Compartilhamento de Schemas | `worker/contracts/backend_api.py` define `JobDetails`/`JobStatusUpdate`/`PresignedUrl`/`ArtifactUploadUrlRequest`/`ArtifactUploadUrl` de forma independente — nenhum import de `app/schemas/schemas.py` | ✓ Limpo |
| Compartilhamento de Services | Nenhuma referência a `app/services/*` | ✓ Limpo |
| Compartilhamento de configurações | `WorkerSettings` é uma classe própria, `.env` próprio. **Nuance revisada:** `WORKER_API_KEY` usa o mesmo *nome* de variável do backend — isso é necessário (os dois lados precisam concordar no mesmo *valor* de segredo para a autenticação funcionar) e já foi justificado explicitamente no plano da W2; não é compartilhamento de arquivo/classe, é a natureza de um segredo compartilhado | ✓ Sem violação, nuance documentada |
| Compartilhamento de banco de dados | Nenhuma dependência de driver de banco (`psycopg`/`asyncpg`/`sqlalchemy`) em `requirements.txt` do Worker | ✓ Limpo |
| Compartilhamento de ambiente virtual | `requirements.txt` próprio; validado em `venv_worker310`, nunca no `venv_gk310` do backend | ✓ Limpo |
| Contratos públicos exclusivos (REST/Redis/R2) | Toda comunicação passa por `BackendClient` (REST), `infrastructure/redis/*` (Redis) e URLs assinadas via `BackendClient.get_download_url`/`get_artifact_upload_url` (R2) | ✓ Nenhum canal alternativo encontrado |

**Veredito: nenhuma violação de Boundary Enforcement.** A única observação é a nuance do `WORKER_API_KEY`, que já era esperada e está corretamente justificada, não uma falha.

---

# 4. Dívida Técnica

1. **`AI_WORKER_CONSTITUTION.md` §1/§12 desatualizados** (já detalhado na Seção 2). É a dívida mais importante porque compromete a premissa de que a Constituição é a fonte única de verdade.
2. **`QueueConnectionError` é código morto.** Definida em `worker/core/exceptions.py`, nunca é levantada — `ensure_consumer_group`, `read_next_job` e `ack_job` deixam exceções cruas do `redis.asyncio`/`redis.exceptions` vazarem sem tradução. Isso quebra silenciosamente a promessa (já enunciada no relatório da W1) de que "todo erro do Worker herda de `WorkerError`".
3. **`BackendClient`/`_BaseBackendClient` não implementam o protocolo de context manager assíncrono** (`__aenter__`/`__aexit__`). Hoje, todo chamador precisa lembrar de chamar `aclose()` manualmente (o script de validação da W2 fez isso corretamente, mas nada impede um esquecimento futuro — inclusive dentro do próprio orchestrator da W3).
4. **`block_ms` de `read_next_job` é um parâmetro com default fixo no código (5000ms), não uma configuração de `WorkerSettings`** — inconsistente com `lock_ttl_seconds`/`consumer_group`, que são configuráveis. Provavelmente precisará virar configurável já na W3.
5. **Nome do stream (`"processing_jobs"`) e o nome dos campos da mensagem (`job_id`/`video_id`) são um contrato replicado como literal de string em dois códigos independentes**, sem nenhum teste de contrato automatizado que rodasse dos dois lados. Hoje isso é mitigado só por comentário/documentação — se o backend renomear o stream no futuro, o Worker vai parar de receber mensagens silenciosamente (sem erro, só ausência de mensagens).
6. **Nenhum commit git existe para `goalkeeper_ai_worker/`** — confirmado nesta revisão (`git status` mostra a pasta inteira como `??`, não rastreada). Dois sprints de trabalho não têm nenhuma proteção de histórico.
7. **Nenhum placeholder existe ainda para `orchestrator/`, `pipeline/` ou `state/`** — ao contrário de `models/`/`infrastructure/storage/`, que foram deliberadamente criados vazios como reserva, esses três módulos (centrais para a W3) não têm nem uma pasta vazia hoje. Não é uma dívida grave, mas é uma inconsistência de padrão (por que reservar `models/`/`storage/` e não esses três?).

Nenhum destes itens é grave isoladamente. Juntos, formam uma lista curta e concreta de "arrumação" recomendada antes ou durante o início da W3.

---

# 5. Escalabilidade

Considerando o horizonte de múltiplos Workers, múltiplas GPUs, múltiplos modelos, múltiplos pipelines, múltiplos tipos de análise e centenas de milhares de vídeos:

- **Múltiplos Workers:** já suportado pelo desenho atual sem nenhuma mudança de código — consumer group do Redis Streams distribui mensagens nativamente entre consumidores, e o Lock por vídeo (testado com dois "donos" diferentes) impede dupla-atuação no mesmo vídeo. Este é o ponto mais forte da arquitetura atual do ponto de vista de escala.
- **Múltiplas GPUs/modelos:** `gpu/`, `registry/`, `models/` seguem vazios — o desenho conceitual (Constituição §6/§7) é adequado no papel, mas não há nenhuma linha de código ainda para avaliar se resistirá à prática. Risco normal de estágio, não uma falha.
- **Múltiplos pipelines/tipos de análise:** aqui há uma lacuna conceitual, não de código — a Constituição versiona **um** Pipeline ao longo do tempo (Pipeline Version, ADR-006), mas não define uma dimensão para **múltiplos tipos de pipeline coexistindo** (ex.: "análise rápida" vs. "análise completa" rodando ao mesmo tempo, cada uma com sua própria sequência de Stages). Se isso se tornar uma necessidade real, `Pipeline Version` pode precisar de um `pipeline_name`/`pipeline_type` como dimensão adicional. Vale registrar como questão em aberto, não como defeito.
- **Centenas de milhares de vídeos:** o gargalo mais concreto e já identificado (Constituição, Risco 7) é o uso de disco do workspace local sob carga — ainda sem nenhuma implementação de quota/limpeza, porque o próprio workspace ainda não existe. Isso precisa ser resolvido já na W3, não pode esperar.
- **Singleton do cliente Redis por processo:** `get_redis_client(settings)` guarda um único cliente global por processo — isso é exatamente o modelo certo para escalar horizontalmente (múltiplos processos Worker, cada um com seu próprio singleton), não uma limitação.

**Veredito de escalabilidade:** as decisões estruturais tomadas até aqui (Redis Streams + consumer group, Lock por vídeo, Worker stateless, Plugin Registry por família) continuam adequadas para o horizonte descrito. Nada do que foi construído precisará ser desfeito para escalar — as lacunas (workspace/disco, múltiplos tipos de pipeline) são coisas ainda não construídas, não decisões erradas já tomadas.

---

# 6. Preparação para W3

A pergunta do roadmap — Redis → Job → Lock → Workspace → Download → Upload → Checkpoint → Fim — foi conferida contra o código real:

| Etapa | Está pronta? |
|---|---|
| Redis (consumir mensagem) | ✓ Pronto (`infrastructure/redis/consumer.py`) |
| Job (buscar detalhes) | ✓ Pronto (`BackendClient.get_job`) |
| Lock | ✓ Pronto (`infrastructure/redis/lock.py`) |
| Workspace temporário | ✗ Não existe nenhum código nem placeholder |
| Download | ✗ `infrastructure/storage/` vazio (deliberado) |
| Upload | ✗ Idem |
| Checkpoint | ✗ Não existe nenhum módulo `state/`, nem placeholder |
| Fim (status + liberar Lock) | ✓ Pronto (`BackendClient.update_job_status` + `lock.release`) |

**A estrutura atual suporta a W3 sem exigir refatoração do que já existe** — tudo que falta é aditivo (módulos novos), não uma reescrita do que a W1/W2 construíram. Esse é o resultado mais importante desta revisão: nenhuma decisão da W1/W2 precisa ser desfeita.

Dito isso, dois pontos precisam de atenção **antes ou logo no início** da W3, para que ela comece no lugar certo:

1. **O `orchestrator/` que a Constituição declara como responsável por "decidir transição entre Stages" ainda não existe.** Sem criá-lo explicitamente, o risco real é `worker/main.py` absorver essa responsabilidade organicamente e virar, ele mesmo, o orchestrator — violando a separação que a própria Constituição pede (§1: "orchestrator... não conhece qual Plugin está ativo", implicitamente também não deveria ser o ponto de entrada do processo).
2. **A dívida técnica dos itens 2, 4 e 5 da Seção 4** (exceção não levantada, timeout não configurável, contrato de stream sem verificação) fica mais barata de corrigir agora, antes de a W3 construir a esteira real por cima dessas mesmas peças.

---

# 7. Recomendações

## Obrigatórias (antes de iniciar a W3)

1. **Atualizar `AI_WORKER_CONSTITUTION.md` §1 e §12** para refletir `infrastructure/` (com `redis/`, `backend_client/`, `storage/`), `contracts/` e `core/` como estrutura oficial — a Constituição precisa voltar a ser a verdade, não um registro histórico do que se pensava antes da W2.
2. **Criar (ao menos como pastas vazias, no mesmo padrão de `models/`) os módulos `orchestrator/`, `pipeline/` e `state/`** antes de começar a escrever a lógica da W3 dentro deles — evita que `main.py` vire um orchestrator informal por omissão.
3. **Decidir e corrigir o destino de `QueueConnectionError`**: ou passa a ser levantada de fato (envolvendo as chamadas Redis em `consumer.py`/`lock.py` num tratamento de exceção), ou é removida até haver um uso real. Uma exceção declarada e nunca usada é uma promessa quebrada silenciosamente.
4. **Fazer o primeiro commit de `goalkeeper_ai_worker/`** — hoje não há nenhuma proteção de histórico para dois sprints inteiros de trabalho.

## Recomendadas (podem esperar até durante a W3, mas não além dela)

5. Tornar `block_ms` (timeout de leitura do consumer group) configurável via `WorkerSettings`, mesmo padrão de `lock_ttl_seconds`.
6. Adicionar suporte a `async with BackendClient(...)` (`__aenter__`/`__aexit__`) para tornar o fechamento de recursos automático, especialmente antes de compor o laço real de consumo na W3.
7. Avaliar um teste de contrato leve (mesmo que só documental/checklist) para o nome do stream Redis e o formato da mensagem, já que hoje é um valor literal duplicado sem verificação cruzada automatizada.

## Opcionais

8. Considerar se `Pipeline Version` (ADR-006) precisará, mais adiante, de uma dimensão adicional de "tipo de pipeline" para suportar múltiplas análises coexistindo — não é urgente, é uma pergunta em aberto para quando essa necessidade for real.
9. Dividir `contracts/backend_api.py` e `infrastructure/backend_client/client.py` por domínio (ex.: `jobs`, `storage`, futuramente `analysis`) quando o número de endpoints crescer o suficiente para justificar — a estrutura já foi deliberadamente preparada para isso na W2, não precisa ser feito agora.

---

## Conclusão

**A arquitetura está madura o suficiente para seguir para a Sprint W3**, com uma ressalva: os 4 itens "Obrigatórios" acima são pequenos, rápidos e não exigem nenhuma decisão nova (nenhum deles reabre uma decisão já congelada) — recomendo tratá-los como uma mini-tarefa de consolidação antes da primeira linha de código da W3, exatamente como foi feito entre a W1 e a W2. Nenhum deles é motivo para atrasar o início da W3 além disso.
