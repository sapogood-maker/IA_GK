# AI_WORKER_CONSTITUTION.md — Goalkeeper AI Worker

**Constituição arquitetural oficial do serviço `goalkeeper_ai_worker`, parte do monorepo `IA_GK`.**

> Documento vivo. A revisão original (antes da primeira linha de código) promoveu toda decisão então registrada como "risco em aberto" ou "nota" a arquitetura principal ou a um ADR explícito. **Sprint W2.1** (pós-Sprint W2, `ARCHITECTURE_REVIEW_W2.md`) sincronizou a Seção 1 e a Seção 12 com a estrutura real implementada (`contracts/`, `infrastructure/`, `core/`) — a Constituição deixou de refletir só a intenção original e passou a refletir também o código real.

## Premissas e escopo

- **Monorepo (ADR-009):** o Worker vive na pasta `goalkeeper_ai_worker/`, dentro do mesmo repositório Git de `IA_GK` (`backend_fastapi/`, `frontend_flutter/`, `goalkeeper_ai_worker/` como pastas de topo irmãs). Decisão puramente organizacional/de versionamento — **nenhuma responsabilidade de componente muda**. O Worker continua sendo tratado como se estivesse em outro repositório: runtime, dependências, código Python, banco de dados e lógica de negócio nunca são compartilhados com `backend_fastapi/` (ver Frozen Architecture, ao final deste documento).
- O Worker **consome** a infraestrutura já construída no backend (Sprints 5-7): autenticação por API Key (`X-Worker-Api-Key`), URLs assinadas de download/upload, Redis Streams (stream `processing_jobs`), e o modelo de dados `Analysis`/`Event`/`Metric`/`Artifact`/`Report`. **Nenhuma dessas peças é alterada aqui.**
- Hardware atual: 1 máquina com GPU AMD RX 7900 XTX (ROCm). Horizonte de 2-3 anos: múltiplas máquinas, múltiplos vendors de GPU, múltiplos modelos de IA coexistindo, dezenas a centenas de vídeos por clube por mês.
- Este documento assume que uma peça específica do backend ainda não existe (o endpoint de submissão de resultados) e trata isso como dependência externa explícita (ver ADR-008), não como algo a implementar agora.

---

## Terminologia Oficial (Glossário)

Termos usados de forma consistente em todo o documento — evitar reintroduzir sinônimos para os mesmos conceitos.

| Termo | Definição |
|---|---|
| **Video** | Asset original enviado pelo usuário via backend. Identificado por `video_id`, estável durante toda a vida do vídeo, mesmo com múltiplas análises. |
| **Job** | Uma tentativa de processamento de um Video. Identificado por `job_id`. Um Video pode ter vários Jobs ao longo do tempo (reprocessamento), mas no máximo **um Job ativo por vez** (ADR-001). |
| **Correlation ID** | `video_id`, formalizado como identificador primário de correlação (Seção 3). |
| **Pipeline** | Sequência ordenada de Stages que processam um Job. Possui versão própria — **Pipeline Version** (Seção 8, ADR-006). |
| **Stage** | Unidade atômica de trabalho dentro do Pipeline (ex.: Download, Inferência, Submissão). Cada Stage tem timeout e classe de retry próprios (Seção 5). |
| **Plugin** | Implementação concreta e substituível de uma família de capacidade (modelo de detecção, tracker, calculadora de métrica, detector de evento, gerador de artefato, gerador de relatório). Todo Plugin tem nome, família e versão, e implementa a Interface de Plugin da sua família. |
| **Plugin Registry** | Componente único que resolve, para uma família de Plugin, qual implementação concreta está ativa, a partir de configuração (Seção 6, ADR-005). |
| **Model Registry** | Especialização do Plugin Registry para modelos de IA (detecção, pose, segmentação, classificação). |
| **Analysis** | Resultado versionado de um Job bem-sucedido sobre um Video. **Nunca sobrescrita** — cada execução bem-sucedida gera uma nova versão. |
| **Event / Metric / Artifact / Report** | Entidades do modelo de dados já definido no backend (Sprint 5), associadas a uma Analysis. |
| **Worker** | O serviço definido por este documento. **Stateless entre Jobs** — não guarda estado de negócio entre execuções; o único estado local é o checkpoint efêmero de um Job em andamento (Seção 5). |
| **Worker Instance** | Um processo Worker em execução, identificado por `worker_instance_id` (o campo já usado como `worker_id` nos testes do backend — mesmo conceito). |
| **Worker Version** | Versão do software do Worker (build/release) — distinta da instância. |
| **Schema Version** | Versão do contrato de dados usado na submissão de resultados ao backend (Seção 9). |

---

## 1. Arquitetura Interna do Worker

Arquitetura hexagonal (ports & adapters): um núcleo de orquestração que não conhece detalhes de infraestrutura, cercado por Plugins e adaptadores substituíveis via Registry.

| Módulo | Responsabilidade | O que NÃO faz |
|---|---|---|
| `orchestrator` | Executa o Pipeline; decide transição entre Stages; aplica timeout/retry/cancelamento (Seção 5) | Não conhece R2, não conhece qual Plugin está ativo |
| `pipeline` | Declara a sequência versionada de Stages (Pipeline Version) | Não implementa os Stages, só os declara |
| `contracts` | Tipos que representam exclusivamente os contratos públicos do Backend — REST (`backend_api.py`) e mensagem do Redis Stream (`queue_message.py`) | Não contém lógica, não importa `app/schemas/schemas.py` do backend (Boundary Enforcement) |
| `infrastructure/redis` | Cliente Redis, consumer group do stream `processing_jobs` (ack/claim/retry de mensagens) e Lock distribuído por `video_id` (Seção 4, ADR-001/003) — os três agrupados por dependerem do mesmo sistema externo | Não decide o que fazer com o Job nem política de negócio, só entrega/confirma mensagens e coordena acesso |
| `infrastructure/backend_client` | Cliente HTTP do Worker API: camada genérica de requisição + detalhes do Job, atualização de status, URLs assinadas, Contrato Backend↔Worker (Seção 9) | Não acessa Postgres/R2 diretamente |
| `infrastructure/storage` | Download/upload via URL assinada; cache local por Job | Não decide quando baixar/subir |
| `gpu` | Abstração de compute (Seção 7) | Não conhece nenhum Plugin específico |
| `registry` | Mecanismo genérico de Plugin Registry, reaproveitado por todas as famílias (Seção 6) | Não implementa nenhum Plugin |
| `models/` | Plugins de modelos de IA (detecção, pose, segmentação, classificação), resolvidos pelo Model Registry | Não sabe o que é um Job ou Video |
| `tracking/` | Plugins de tracking | Idem |
| `metrics/` | Plugins de métricas (Metric Registry) | Idem |
| `events/` | Plugins de eventos (Event Registry) | Idem |
| `artifacts/` | Plugins de artefatos (Artifact Registry) | Idem |
| `report/` | Plugins de relatório (Report Registry) | Não persiste nada — só agrega |
| `submission` | Monta e envia o payload do Contrato Backend↔Worker em duas fases idempotentes (Seção 9) | Não gera dados, só os empacota e envia |
| `state` | Checkpoint efêmero local do Job em andamento | Não é banco de dados de produção |
| `workspace` | Gerencia o diretório de trabalho temporário por Job (criação/limpeza) — distinto do diretório de dados `goalkeeper_ai_worker/workspace/` (Seção 12), que é o local físico gerenciado por este módulo | Não decide o que gravar ali — só oferece o espaço |
| `observability` | Logging estruturado (Correlation ID obrigatório), métricas internas, heartbeat, health check | Não decide política de alerta |
| `core` | Ciclo de vida do processo (inicialização, shutdown gracioso) e hierarquia de exceções própria (`WorkerError`) | Não contém lógica de negócio nem de infraestrutura externa |
| `config` | Seleção de Plugins ativos, versões, TTLs, timeouts | Não contém lógica de negócio |

**Regra de dependência (Frozen):** `orchestrator`, `pipeline`, `metrics`, `events` só dependem de **interfaces**. Adaptadores concretos (`models/yolo`, `gpu/rocm`) implementam essas interfaces e são conectados pelo `registry`, nunca por import direto do núcleo.

---

## 2. Pipeline e Estágios (Stages)

Cada Stage recebe um contexto de execução do Job (metadados + caminhos de arquivos intermediários) e devolve o contexto atualizado. Nenhum Stage acessa estado global. Ordem oficial:

1. **Recepção do Job** — `queue` entrega uma mensagem (`job_id`, `video_id`) do consumer group. O `orchestrator` confirma via `backend_client` que o Job ainda está em estado consumível, **então adquire o Lock do vídeo** (Seção 4) — nenhum Job avança sem o lock. Cria o workspace local.
2. **Download** — `storage` obtém a URL assinada de download e baixa o vídeo original.
3. **Validação** — verifica integridade/formato. Falha aqui é sempre permanente.
4. **Pré-processamento** — normalização (frame rate, resolução) e extração/indexação de frames.
5. **Inferência** — Plugins de detecção/pose/segmentação/classificação (Model Registry) rodam de forma independente entre si.
6. **Tracking** — associa detecções entre frames em entidades com ID persistente.
7. **Pós-processamento** — suavização de trajetórias, correção de gaps/IDs trocados.
8. **Métricas** — Plugins do Metric Registry calculam valores a partir das trajetórias.
9. **Eventos** — Plugins do Event Registry produzem eventos discretos a partir de trajetórias e métricas.
10. **Artefatos** — Plugins do Artifact Registry geram arquivos localmente no workspace.
11. **Upload** — `storage` envia os bytes dos artefatos ao R2 via URL assinada de upload (esquema `artifacts/{video_id}/{job_id}/{filename}` já definido pelo backend).
12. **Relatório** — Plugins do Report Registry agregam métricas/eventos/artefatos (já com seus `r2_key` conhecidos) num payload de relatório.
13. **Submissão de Resultados** — `submission` executa as duas fases idempotentes do Contrato Backend↔Worker (Seção 9): cria/obtém a Analysis, depois envia Events/Metrics/Artifacts(metadados)/Report referenciando-a.
14. **Conclusão** — só ocorre **depois** que a Submissão (etapa 13) foi confirmada com sucesso. `backend_client` marca o Job como `COMPLETED` (ou `FAILED`, se qualquer etapa anterior falhou permanentemente), e o Lock do vídeo é liberado.

Cada Stage grava um checkpoint local antes de iniciar e depois de concluir com sucesso (retomada — Seção 5).

---

## 3. Correlation ID e Rastreabilidade

**`video_id` é o Correlation ID oficial** — presente obrigatoriamente em todo log, métrica interna e payload de submissão, tanto no Worker quanto no backend. Ele é estável entre reprocessamentos (múltiplos Jobs do mesmo vídeo), o que um `job_id` isolado não garante, e não exige criar um identificador novo, pois já existe em todo o sistema desde o upload.

**`job_id` representa apenas uma tentativa específica de processamento** — um identificador secundário e descartável, nunca reutilizado como chave de correlação de longo prazo. Toda linha de log deve conter os dois: `video_id` (correlação primária) e `job_id` (tentativa atual).

---

## 4. Exclusão Mútua por Vídeo (Lock Distribuído)

Mecanismo oficial (ADR-001) para impedir que dois Workers processem o mesmo Video simultaneamente:

- Lock distribuído no Redis, chave derivada de `video_id`, adquirido como a **primeira ação** do Stage "Recepção do Job" (Seção 2) — nenhum download, nenhuma inferência, nenhuma escrita começa sem o lock adquirido.
- TTL curto com renovação periódica automática atrelada ao heartbeat do Worker (ADR-003) — um Worker que para de reportar liveness perde o lock automaticamente, permitindo que outro Worker assuma.
- Liberado explicitamente ao final do Stage "Conclusão" (sucesso ou falha permanente) e, de forma graciosa, em caso de cancelamento (Seção 5).
- É a defesa primária. Uma defesa complementar no backend (rejeitar criação de um novo Job enquanto há um ativo para o mesmo vídeo) é recomendada como evolução futura, coordenada como mudança de backend — não implementada neste repositório.

---

## 5. Política de Timeout, Retry, Cancelamento e Retomada

| Situação | Ação oficial |
|---|---|
| Falha transitória num Stage retryable (rede, timeout de I/O) | Retry com backoff exponencial, limite de N tentativas configurável por Stage; checkpoint do Stage não avança até sucesso |
| Timeout de um Stage (excedeu o orçamento máximo de tempo declarado para aquele Stage) | Aborta a tentativa atual do Stage e aplica a mesma política de retry acima — o Job inteiro não é abortado só por um Stage estourar o tempo, a menos que o limite de tentativas também se esgote |
| Falha permanente (vídeo corrompido, erro de modelo não recuperável, validação reprovada) | Job vai para `FAILED` com `error_message` descritivo; mensagem confirmada (`ACK`) na fila — não é reprocessada automaticamente; Lock liberado |
| Cancelamento externo (`CANCELLED` solicitado via backend, por ação humana) | O Worker consulta o status do Job junto ao `backend_client` nos pontos de checagem entre Stages (ADR-004); ao detectar `CANCELLED`, interrompe no próximo ponto seguro, libera o Lock, **não** executa a Submissão de Resultados |
| Crash do processo Worker | Mensagem não confirmada permanece pendente no consumer group; após timeout, outro Worker reivindica via `XCLAIM`; se houver checkpoint local (mesma máquina), retoma do último Stage concluído; senão recomeça do início (risco aceito, ver Riscos Arquiteturais) |
| Esgotamento do limite de retries num Stage retryable | Job vai para `FAILED`, tratado como falha permanente a partir desse ponto — não fica retentando indefinidamente |

Cancelamento é sempre **gracioso**: nunca ocorre no meio de uma operação não interrompível com segurança (ex.: nunca no meio do envio da Fase 2 da Submissão — o Worker termina a fase em andamento antes de respeitar um cancelamento pendente).

---

## 6. Arquitetura de Plugins (Plugin Registry Único)

**Um único contrato de Plugin, um único mecanismo de Registry**, reaproveitado por todas as famílias — evita seis padrões ad hoc ligeiramente diferentes.

- **Contrato de Plugin:** nome, família, versão, interface de entrada/saída própria da família, ciclo de vida (`init` → `execute` → `teardown`).
- **Plugin Registry:** resolve, para uma família, qual Plugin está ativo (por versão), a partir de configuração. Descoberta automática de Plugins existentes + ativação explícita por configuração (ADR-005) — nenhum Plugin roda sem estar habilitado.
- **Independência entre famílias:** Plugins de famílias diferentes (detecção, pose, segmentação, classificação, tracking, métricas, eventos, artefatos, relatório) não têm dependência de código entre si — só compartilham o contrato de dados produzido/consumido em cada transição do Pipeline (Seção 2). Adicionar uma família nova (ex.: um sétimo tipo de modelo) não altera as demais.

**Especializações do Plugin Registry:**

| Registry | Família | Exemplos de Plugin |
|---|---|---|
| **Model Registry** | Detecção, pose, segmentação, classificação | YOLO, RT-DETR, Grounding DINO, SAM2, modelo próprio |
| **Tracker Registry** | Tracking | ByteTrack, DeepSORT, ou outro |
| **Metric Registry** | Métricas | Cada calculadora de métrica |
| **Event Registry** | Eventos | Defesa, Saída, Reposição, 1x1, Cruzamento |
| **Artifact Registry** | Artefatos | thumbnail, heatmap, timeline, json, vídeo anotado, clipes, csv, parquet |
| **Report Registry** | Relatório | Relatório técnico detalhado, resumo para treinador, outros formatos de agregação |

Trocar um Plugin (ex.: YOLO por RT-DETR) é escrever um novo Plugin conforme o contrato da família + apontar o Registry para ele via configuração — zero mudança em `orchestrator`, `pipeline`, ou em qualquer outra família.

---

## 7. Abstração de GPU (Compute Backend)

Interface "Compute Backend": seleção de dispositivo, alocação/liberação de memória e política de fallback resolvidas por um adaptador de compute, nunca espalhadas pelos Plugins de modelo. Hoje: adaptador ROCm (AMD). Futuro: adaptador CUDA. Depois: adaptador CPU (fallback com degradação aceita).

Frameworks de deep learning já abstraem boa parte da diferença ROCm/CUDA no nível de tensor, mas o Worker ainda precisa de uma camada própria para: seleção de dispositivo na inicialização, tamanho de lote adaptativo conforme memória disponível, tratamento de OOM com fallback, e relato de qual dispositivo está em uso (Observabilidade). Nenhum Plugin de modelo, tracker ou Stage do Pipeline verifica diretamente "estou em ROCm ou CUDA?".

---

## 8. Versionamento e Rastreabilidade Completa

Toda **Analysis** produzida carrega, como metadados de proveniência, as seguintes versões — sem isso não há como auditar retroativamente o que gerou um resultado:

- **Pipeline Version** — identifica a sequência de Stages e o conjunto de Plugins ativos no momento da execução (ADR-006). Versão única por execução do Pipeline inteiro.
- **Worker Version** — versão do software do Worker que processou o Job (distinta do `worker_instance_id`, que identifica só a instância física/processo).
- **Model Versions** — mapa família → versão de cada Plugin de modelo efetivamente usado (Model Registry), persistido por hash de conteúdo dos pesos, não apenas por tag semântica (ADR-007).
- **Schema Version** — versão do contrato de submissão (Seção 9) usado para montar o payload.

Essas quatro versões são obrigatoriamente incluídas no payload da Submissão de Resultados (Seção 9) e devem ser persistidas junto da Analysis correspondente no backend — a exigência de captura é definida aqui; o campo/coluna exato de persistência é uma decisão de schema do backend, fora do escopo deste repositório, mas dependente desta arquitetura.

---

## 9. Contrato Backend ↔ Worker

Autenticação inalterada: API Key existente (`X-Worker-Api-Key`).

**Submissão de Resultados em duas fases idempotentes (ADR-002, ADR-008):**

- **Fase 1 — Criar/Obter Analysis:** o Worker solicita a criação de uma Analysis para `(video_id, job_id)`. Idempotente: se uma Analysis já existir para esse `job_id` (ex.: reenvio após falha de rede na Fase 2), o backend devolve a existente em vez de criar uma duplicata. A atribuição da versão da Analysis é responsabilidade exclusiva do backend (autoridade única de escrita), eliminando corrida de versionamento mesmo sob concorrência.
- **Fase 2 — Enviar Resultados:** o Worker envia, referenciando a Analysis da Fase 1: os Events, as Metrics, os metadados de Artifact (apontando para os `r2_key` já enviados na etapa de Upload — a Fase 2 nunca envia bytes, só metadados) e o Report. Idempotente por Analysis + chave natural de cada item — seguro reenviar a Fase 2 inteira se ela falhou parcialmente.
- O Job só é marcado `COMPLETED` (Stage "Conclusão", Seção 2) **depois** que a Fase 2 é confirmada com sucesso pelo backend.
- O payload da Fase 2 carrega `schema_version`, `pipeline_version`, `worker_version`, `model_versions` e o Correlation ID (`video_id`) — ver Seção 8.

**Dependência externa explícita:** as Fases 1 e 2 não existem hoje no backend. Este documento assume que serão implementadas como uma pequena sprint do repositório backend, coordenada antes da Sprint W8 do roadmap do Worker (Seção 13) — ver ADR-008.

---

## 10. Escalabilidade

- **Distribuição de carga:** todos os Workers se inscrevem no mesmo consumer group do stream `processing_jobs`; o Redis distribui as mensagens automaticamente.
- **Exclusão mútua por vídeo** (Seção 4) é complementar à distribuição por Job — o consumer group evita que a *mesma mensagem* seja entregue duas vezes; o Lock evita que *Jobs diferentes do mesmo vídeo* rodem ao mesmo tempo.
- **Recuperação de falhas:** mensagens não confirmadas ficam pendentes; qualquer Worker vivo pode reivindicá-las via `XCLAIM` após timeout.
- **Recurso físico limitado (GPU):** hoje uma única GPU. Escalar para 10-100 Workers pressupõe múltiplas máquinas com GPU — decisão de infraestrutura/operação, não de arquitetura de código.

---

## 11. Observabilidade

- **Logs estruturados** com `video_id` (Correlation ID) e `job_id` obrigatórios em toda linha relacionada a um Job (Seção 3).
- **Métricas internas:** duração por Stage, throughput, profundidade/lag da fila, taxa de falha, contagem de retries, utilização de GPU/memória — formato compatível com Prometheus é evolução futura, não exigência agora.
- **Heartbeat:** reportado periodicamente pelo Worker, e é o mesmo sinal que sustenta a renovação do Lock de vídeo (Seção 4, ADR-003).
- **Health check:** verificação local de conectividade com Redis, backend e GPU.
- **Tracing:** o Correlation ID já cobre a reconstrução de uma execução ponta a ponta via log; OpenTelemetry é evolução possível, não bloqueante.

---

## 12. Estrutura Completa do Repositório

```
IA_GK/                                # monorepo oficial - um unico Git, dois produtos independentes (ADR-009)
├── backend_fastapi/                  # Produto 1: Plataforma SaaS - fora do escopo deste documento
├── frontend_flutter/                 # Produto 1: Flutter Web - fora do escopo deste documento
├── goalkeeper_ai_worker/             # Produto 2: este documento - servico de IA, totalmente independente
│   ├── worker/
│   │   ├── orchestrator/        # (vazio ate a W3) executa o Pipeline; timeout/retry/cancelamento por Stage
│   │   ├── pipeline/            # (vazio ate a W3) sequencia declarada de Stages; Pipeline Version
│   │   ├── contracts/            # tipos dos contratos publicos do Backend (REST + mensagem do Redis Stream)
│   │   │   ├── backend_api.py     # JobDetails, JobStatusUpdate, PresignedUrl, ArtifactUploadUrlRequest/Response
│   │   │   └── queue_message.py    # JobMessage (job_id, video_id, message_id)
│   │   ├── infrastructure/        # clientes de infraestrutura externa, agrupados por sistema
│   │   │   ├── redis/              # cliente Redis, consumer group (queue), Lock por video_id (ADR-001/003)
│   │   │   ├── backend_client/      # Worker API: camada HTTP generica + job/status/URLs assinadas
│   │   │   └── storage/              # (vazio ate a W3) download/upload REAL via URL assinada
│   │   ├── gpu/                 # (vazio ate a W4) Compute Backend + adaptadores (rocm/, cuda/, cpu/)
│   │   ├── registry/            # (vazio ate a W4) mecanismo generico de Plugin Registry
│   │   ├── models/               # (vazio ate a W4)
│   │   │   ├── detection/        # Plugins: yolo/, rtdetr/, grounding_dino/, proprio/
│   │   │   ├── pose/
│   │   │   ├── segmentation/
│   │   │   └── classification/
│   │   ├── tracking/              # (vazio ate a W5) Plugins de tracker
│   │   ├── metrics/                # (vazio ate a W5) Plugins de metrica (Metric Registry)
│   │   ├── events/                  # (vazio ate a W5) Plugins de evento (Event Registry)
│   │   ├── artifacts/                # (vazio ate a W5) Plugins de artefato (Artifact Registry)
│   │   ├── report/                    # (vazio) Plugins de relatorio (Report Registry)
│   │   ├── submission/                 # (vazio) Fases 1 e 2 do Contrato Backend<->Worker
│   │   ├── state/                       # (vazio ate a W3) checkpoint efemero local por Job
│   │   ├── workspace/                    # (vazio ate a W3) gerencia o diretorio de trabalho por Job
│   │   ├── observability/                # logging (pronto); metricas internas, heartbeat, health check (futuro)
│   │   ├── core/                          # ciclo de vida do processo e hierarquia de excecoes (WorkerError)
│   │   └── config/                        # selecao de Plugins ativos, versoes, TTLs, timeouts
│   ├── requirements.txt              # dependencias proprias - NUNCA compartilhadas com backend_fastapi/
│   ├── pyproject.toml                # metadados do projeto + configuracao do pytest
│   ├── .env.example                  # variaveis documentadas, nenhum valor sensivel real
│   ├── .gitignore                    # .venv/, __pycache__/, weights/, workspace/ (proprio, nao o do IA_GK)
│   ├── README.md                     # status da sprint atual, como rodar/testar
│   ├── weights/                       # NAO versionado no git - pesos de modelo (hash de conteudo) - W4+
│   ├── workspace/                     # NAO versionado no git - area de trabalho temporaria por Job - W3+
│   ├── docs/                          # (ainda nao criado) documentacao especifica de implementacao do Worker
│   │   ├── architecture/
│   │   └── adr/                       # ADRs de implementacao (ex.: escolha de biblioteca de tracking) -
│   │                                  # distintas das ADRs constitucionais desta Constituicao
│   ├── scripts/                        # (ainda nao criado) utilitarios operacionais (nao Docker, nao IA)
│   └── tests/                          # implementado desde a W1 - tests/ (unitarios) e tests/infrastructure/
│                                        # (integracao com Redis real, HTTP mockado)
└── docs/                             # documentacao do monorepo (AI_WORKER_ARCHITECTURE.md,
                                       # AI_WORKER_CONSTITUTION.md e DOMAIN_ARCHITECTURE.md residem
                                       # hoje na raiz do IA_GK - reorganizacao para docs/ e um
                                       # follow-up ainda nao decidido, nao executado nesta revisao)
```

**Regra de isolamento (Frozen):** nenhum `import` cruza a fronteira entre `backend_fastapi/` e `goalkeeper_ai_worker/`, em nenhuma direção. `goalkeeper_ai_worker/` tem `requirements.txt`, ambiente Python e ciclo de deploy inteiramente próprios — a única coisa que os dois compartilham é o histórico do Git.

---

## 13. Roadmap

Cada sprint é totalmente funcional. **Revisado após a conclusão da Sprint W1** — substitui o detalhamento fino original por um roadmap de sprints mais amplas, aprovado explicitamente pelo usuário.

| Sprint | Objetivo | Escopo |
|---|---|---|
| **W1 — Fundação** ✓ concluída | Esqueleto do projeto, sem IA, sem integração externa | Estrutura do projeto Python independente, configuração centralizada (`config/`), logging estruturado (`observability/`), ciclo de vida do processo com shutdown gracioso (`core/`), ambiente/dependências/testes próprios. Nenhuma conexão com Redis, API do backend, R2 ou GPU. |
| **W2 — Comunicação** | Integração com os três contratos públicos do Boundary Enforcement | Redis (consumer group do stream `processing_jobs`), `backend_client` (Worker API, autenticado por API Key), acesso ao R2 via URLs assinadas de download/upload, Lock distribuído por vídeo (ADR-001/003). Ainda sem processar nenhum Job de verdade — objetivo é provar que os três canais de comunicação funcionam de ponta a ponta. |
| **W3 — Pipeline de Processamento** | Orquestração completa do ciclo de um Job, ainda sem IA | Download real do vídeo, Upload real de um artefato, Retry e Timeout por Stage (Seção 5), Checkpoint local e retomada (Seção 3/5). Prova a esteira ponta a ponta com um Pipeline "vazio" no lugar da Inferência/Tracking/Métricas/Eventos. |
| **W4 — Primeira IA** | Primeiro modelo real de visão computacional | Camada `gpu/` (Compute Backend, adaptador ROCm), Plugin Registry genérico implementado, primeiro Plugin de detecção real (OpenCV/PyTorch/YOLO) resolvido via Model Registry. |
| **W5 — Pipeline Cognitivo e Artefatos** | Tracking, Métricas, Eventos e Artefatos reais | Tracker Registry, Metric Registry, Event Registry e Artifact Registry, cada um com pelo menos um Plugin real. |

Itens que continuam arquiteturalmente definidos e congelados (ADRs e Seções correspondentes), mas cujo sequenciamento exato após a W5 será revisado quando a W5 concluir: Contrato Backend↔Worker (Seção 9, ADR-002/008), Versionamento completo (Seção 8, ADR-006/007), Report Registry (Seção 6), Observabilidade avançada — métricas internas/heartbeat/health check (Seção 11), Escala horizontal (Seção 10).

---

## 14. Riscos Arquiteturais

1. **Checkpoint local não é durável entre máquinas.** Se outra máquina reivindica o Job via `XCLAIM`, não há checkpoint compartilhado — recomeça do zero nessa máquina. Aceito por simplicidade; reavaliar se crashes frequentes tornarem isso caro na prática.
2. **Redis como único ponto de coordenação** (fila, Lock e heartbeat). Se o Redis cair, publicação, consumo, exclusão mútua e renovação de lock param juntos. Decisão herdada do backend (Sprint 7); reconhecida como ponto único de falha.
3. **A promessa de "trocar Plugin sem alterar o Pipeline" é arquitetural, não física** — frameworks nem sempre têm suporte estável a ROCm para toda arquitetura de modelo recente (ex. SAM2, Grounding DINO).
4. **Padrão de Registry em todo lugar é investimento antecipado** para o dia 1 (1 modelo, 1 tracker) — deliberado, dado o horizonte de 2-3 anos, mas reconhecidamente mais estrutura do que o mínimo necessário na Sprint W1.
5. **Heartbeat como base da renovação do Lock (ADR-003)** cria acoplamento: um bug de heartbeat (sem crash real) liberaria o Lock indevidamente enquanto o Job ainda roda — requer monitoramento dedicado desse caminho.
6. **Armazenamento/versionamento de pesos de modelo** — o princípio está definido (fora do Git, versionado por hash), mas o mecanismo concreto (bucket dedicado vs. volume compartilhado) segue em aberto, a fechar antes da W3.
7. **Uso de disco local sob carga** — múltiplos Jobs concorrentes na mesma máquina exigem disciplina de quota/limpeza do workspace; sem isso, risco real de esgotamento de disco.
8. **Granularidade de campos de proveniência no backend** (Seção 8) depende de uma mudança de schema ainda não desenhada em detalhe no backend — a obrigação de existir está definida aqui, o desenho exato da coluna/tabela não.
9. **Isolamento entre `backend_fastapi/` e `goalkeeper_ai_worker/` depende de disciplina manual, não de imposição automatizada** (ADR-009) — não há, nesta fase, lint ou verificação de CI que bloqueie um `import` cruzado entre as duas pastas do monorepo. O risco de acoplamento silencioso é real e deve ser checado ativamente a cada sprint, não apenas assumido como resolvido pela documentação.

---

# Architecture Decision Records (ADR)

### ADR-001 — Estratégia de lock distribuído por vídeo

- **Contexto:** múltiplos Workers podem reivindicar Jobs distintos do mesmo Video (reprocessamento) sem nenhuma coordenação hoje.
- **Problema:** como impedir dois Workers processando o mesmo Video simultaneamente, evitando corrida de versionamento na Analysis e desperdício de GPU.
- **Alternativas consideradas:** (a) lock distribuído no Redis por `video_id`; (b) serialização no backend, rejeitando criação de novo Job enquanto há um ativo; (c) nenhuma proteção, confiando na unicidade de versão do banco para rejeitar depois do fato.
- **Vantagens:** (a) não exige mudança de backend, reaproveita dependência já existente do Worker no Redis, reação imediata (antes de gastar GPU). (b) defesa na origem, evita até criar o segundo Job. (c) mais simples, zero código novo.
- **Desvantagens:** (a) mais um componente de coordenação para manter correto (TTL, renovação). (b) exige mudança de backend, fora do escopo deste repositório. (c) descobre o conflito tarde demais, depois de gastar processamento inteiro.
- **Decisão recomendada:** (a) como mecanismo primário, com (b) recomendada como defesa complementar futura, coordenada com o backend.
- **Impacto futuro:** introduz dependência do Worker numa primitiva de lock do Redis; exige TTL e renovação (ADR-003).

### ADR-002 — Payload incremental versus payload único de submissão

- **Contexto:** o resultado de um Job pode incluir dezenas de eventos, várias métricas e múltiplos artefatos.
- **Problema:** como estruturar o envio dos resultados ao backend.
- **Alternativas consideradas:** (a) payload único atômico ao final de tudo; (b) incremental por tipo de dado, enviado assim que calculado; (c) duas fases — criar a Analysis, depois enviar tudo relacionado de uma vez.
- **Vantagens:** (a) simples de implementar. (b) resiliente a falhas parciais, não perde trabalho já enviado. (c) equilibra simplicidade com resiliência, sem multiplicar chamadas.
- **Desvantagens:** (a) uma falha de rede no final descarta todo o trabalho e exige reenviar um payload potencialmente grande. (b) multiplica chamadas HTTP e a complexidade de idempotência por tipo de dado. (c) ainda depende de reenvio integral da Fase 2 em caso de falha parcial dela.
- **Decisão recomendada:** (c) — duas fases idempotentes (Seção 9), equilibrando simplicidade operacional com resiliência a retry.
- **Impacto futuro:** define o formato do Contrato Backend↔Worker; qualquer novo tipo de dado (ex. novo tipo de evento) se encaixa na Fase 2 sem alterar a Fase 1.

### ADR-003 — TTL e renovação automática do lock

- **Contexto:** o Lock de vídeo (ADR-001) precisa expirar se o Worker morrer, mas não pode expirar durante um Job legítimo e longo.
- **Problema:** qual duração de TTL adotar e como renová-lo.
- **Alternativas consideradas:** (a) TTL fixo, longo o suficiente para o pior caso, sem renovação; (b) TTL curto com renovação periódica atrelada ao heartbeat; (c) sem TTL, liberação só manual/por conclusão explícita.
- **Vantagens:** (a) simples, sem lógica de renovação. (b) reage rápido a um Worker morto (TTL curto), sem risco de expirar durante um Job vivo (renovação contínua). (c) nunca expira por engano.
- **Desvantagens:** (a) TTL longo o suficiente para o pior caso significa esperar muito tempo para liberar o lock de um Worker morto no caso comum. (b) acopla o Lock à confiabilidade do heartbeat. (c) um Worker morto sem liberação explícita trava o vídeo para sempre.
- **Decisão recomendada:** (b) — TTL curto (ordem de minutos) com renovação a cada fração do TTL, usando o mesmo heartbeat da Seção 11.
- **Impacto futuro:** falha no heartbeat (bug, não crash) libera o Lock indevidamente enquanto o Job ainda roda — risco já registrado na Seção 14, item 5, a monitorar ativamente.

### ADR-004 — Cancelamento de processamento

- **Contexto:** `CANCELLED` já existe como status oficial no backend, mas não havia mecanismo do Worker perceber isso durante o processamento.
- **Problema:** como propagar um pedido de cancelamento (originado por humano no backend) até um Worker no meio de um Job.
- **Alternativas consideradas:** (a) polling do status do Job entre Stages via `backend_client`; (b) canal pub/sub dedicado no Redis para cancelamento; (c) sem suporte a cancelamento em andamento, só preventivo (antes do Job ser reivindicado).
- **Vantagens:** (a) reaproveita infraestrutura já existente, sem canal adicional. (b) reação mais imediata, não depende de o Worker estar entre Stages. (c) mais simples de implementar.
- **Desvantagens:** (a) latência de reação limitada à duração do Stage atual. (b) exige um segundo canal de comunicação e sua própria confiabilidade. (c) não atende ao requisito de cancelamento em andamento pedido nesta revisão.
- **Decisão recomendada:** (a) — polling entre Stages, com latência aceitável dado que Stages têm timeout curto (Seção 5).
- **Impacto futuro:** todo Stage do orchestrator precisa de um ponto de checagem de cancelamento antes de iniciar.

### ADR-005 — Estratégia de descoberta de plugins

- **Contexto:** múltiplas famílias de Plugins precisam ser conhecidas pelo Plugin Registry.
- **Problema:** como o Registry sabe quais Plugins existem e quais estão disponíveis para uso.
- **Alternativas consideradas:** (a) registro explícito em configuração (lista curada); (b) descoberta automática por convenção de diretório/entrypoints; (c) híbrido — descoberta automática, ativação por configuração.
- **Vantagens:** (a) totalmente previsível e seguro. (b) nenhum Plugin escrito é esquecido. (c) combina os dois benefícios.
- **Desvantagens:** (a) fácil esquecer de registrar um Plugin novo. (b) qualquer código na convenção de pastas roda automaticamente — risco de segurança/previsibilidade. (c) exige manter duas listas conceituais (o que existe vs. o que está ativo).
- **Decisão recomendada:** (c) — descoberta automática + ativação explícita por configuração; nenhum Plugin roda sem estar habilitado.
- **Impacto futuro:** exige convenção estável de estrutura de diretórios (Seção 12); mudar essa convenção exige atualizar o mecanismo de descoberta.

### ADR-006 — Versionamento do pipeline

- **Contexto:** a lógica do Pipeline (sequência de Stages, Plugins ativos) evolui; sem versionamento não há como saber o que gerou uma Analysis antiga.
- **Problema:** qual granularidade de versionamento adotar.
- **Alternativas consideradas:** (a) versão única para o Pipeline inteiro; (b) versão independente por família de Stage; (c) sem versionamento.
- **Vantagens:** (a) simples de raciocinar e comparar entre execuções. (b) granularidade fina, permite saber exatamente o que mudou.
- **Desvantagens:** (a) uma mudança pequena em qualquer parte incrementa a versão inteira. (b) explosão combinatória de versões a rastrear e comparar.
- **Decisão recomendada:** (a) — Pipeline Version única como identificador primário de reprodutibilidade, complementada pelo detalhe fino já capturado em Model Versions (Seção 8) — evita a complexidade combinatória de (b) sem perder rastreabilidade.
- **Impacto futuro:** exige disciplina da equipe para incrementar a Pipeline Version a cada mudança de Stage ou Plugin ativo, por menor que seja.

### ADR-007 — Versionamento dos modelos

- **Contexto:** Plugins de modelo precisam ser versionados, armazenados e permitir rollback, sem acoplar o Pipeline a uma implementação específica.
- **Problema:** como versionar e persistir qual versão de modelo gerou um resultado.
- **Alternativas consideradas:** (a) versionamento por hash de conteúdo dos pesos; (b) versionamento por tag semântica manual; (c) ambos.
- **Vantagens:** (a) integridade garantida, impossível ambiguidade. (b) legível e fácil de configurar/selecionar. (c) soma os dois benefícios.
- **Desvantagens:** (a) sozinho, pouco amigável para configuração humana. (b) sozinho, uma tag pode ser reapontada para pesos diferentes por engano, quebrando reprodutibilidade silenciosamente.
- **Decisão recomendada:** (c) — tag semântica como identificador de configuração no Model Registry, hash de conteúdo como o que é efetivamente persistido na proveniência da Analysis (Seção 8).
- **Impacto futuro:** o processo de publicação de novos pesos deve sempre calcular e registrar o hash; hash já publicado nunca é sobrescrito — mesma disciplina de imutabilidade já aplicada à Analysis.

### ADR-008 — Contrato Backend ↔ Worker

- **Contexto:** o Worker precisa entregar resultados estruturados ao backend; esse endpoint não existe hoje.
- **Problema:** qual formato/protocolo adotar, dado que o backend não é alterado nesta sprint mas a decisão precisa existir agora para não bloquear o desenho do Worker.
- **Alternativas consideradas:** (a) contrato síncrono HTTP em duas fases (Seção 9); (b) contrato assíncrono via um segundo stream Redis, consumido pelo backend; (c) escrita direta do Worker no banco — **rejeitada permanentemente**, viola a regra de que o Worker nunca acessa o banco diretamente (ver Frozen Architecture).
- **Vantagens:** (a) reaproveita o mesmo `backend_client`/API Key já usados para todo o resto, um único canal de comunicação. (b) desacopla temporalmente Worker e backend.
- **Desvantagens:** (a) submissão síncrona depende da disponibilidade do backend no momento da conclusão. (b) introduz um segundo canal de comunicação só para este caso, mais complexidade operacional.
- **Decisão recomendada:** (a) — HTTP síncrono em duas fases, mantendo um único canal de comunicação Worker→backend.
- **Impacto futuro:** é a decisão que mais bloqueia trabalho real do Worker (Sprint W8) — deve estar implementada no backend antes dessa sprint; atraso nessa dependência atrasa diretamente o roadmap a partir da W8.

### ADR-009 — Repositório separado versus monorepo

- **Contexto:** a versão original de `AI_WORKER_ARCHITECTURE.md` (Seção 8) recomendava um repositório Git separado (`goalkeeper-ai-worker`) para o Worker, com a justificativa de reforçar organizacionalmente sua independência e evitar a tentação de acoplamento com o backend. Essa recomendação foi revisada após avaliação do fluxo real de desenvolvimento.
- **Problema:** onde o código do Worker deve residir — em um repositório Git próprio, ou dentro do mesmo repositório do backend (`IA_GK`), como uma pasta de topo independente.
- **Alternativas consideradas:** (a) repositório separado (`goalkeeper-ai-worker`) — decisão original; (b) monorepo, com `goalkeeper_ai_worker/` como pasta de topo dentro de `IA_GK`, mantendo independência total de runtime/dependências/código como regra arquitetural explícita; (c) monorepo sem nenhuma barreira formal entre as pastas — rejeitada de imediato, pois abriria caminho direto para acoplamento silencioso.
- **Vantagens:** (a) reforça o isolamento no nível organizacional, dificulta fisicamente qualquer `import` cruzado, permite ciclos de release completamente independentes desde o primeiro commit. (b) preserva contexto entre backend e Worker durante o desenvolvimento (revisões arquiteturais completas do sistema, histórico de decisões num lugar só, sem perda de contexto entre sessões), evita a sobrecarga de coordenar dois repositórios/PRs para mudanças que afetam o contrato entre os dois lados, simplifica a operação para uma equipe pequena.
- **Desvantagens:** (a) exige coordenar mudanças de contrato entre dois repositórios/PRs, duplica configuração inicial (lint, CI, README). (b) exige disciplina ativa — não apenas documental — para que a barreira de independência não seja violada só porque o código está fisicamente acessível no mesmo working tree; o risco de acoplamento silencioso (import cruzado, dependência compartilhada por engano) precisa ser mitigado por regra explícita e revisão manual a cada sprint, já que a estrutura de pastas sozinha não impede fisicamente um `import`.
- **Decisão recomendada:** (b) monorepo, com a barreira de independência tratada como regra arquitetural obrigatória (ver Frozen Architecture) em vez de uma barreira física de repositórios. Nenhuma responsabilidade de componente muda — apenas a organização de versionamento.
- **Impacto futuro:** qualquer `import` entre `backend_fastapi/` e `goalkeeper_ai_worker/`, em qualquer direção, passa a ser tratado como violação arquitetural, verificada manualmente a cada sprint (Seção "Forma de Trabalhar" do processo do projeto) — não há, nesta fase, imposição automatizada (lint/CI) dessa regra, o que é registrado como risco na Seção 14. Se essa disciplina falhar na prática de forma recorrente, a decisão pode ser revertida para (a) sem impacto em nenhuma responsabilidade já definida.

---

# Boundary Enforcement

Backend (`backend_fastapi/`) e Goalkeeper AI Worker (`goalkeeper_ai_worker/`) são sistemas independentes. A presença de ambos no mesmo repositório Git (monorepo, ADR-009) **não altera essa independência em nenhum grau**.

## Proibições absolutas

Nenhum dos itens abaixo é permitido, em qualquer direção, entre `backend_fastapi/` e `goalkeeper_ai_worker/`:

| Proibido | Detalhe |
|---|---|
| Imports cruzados | Nenhum módulo de um lado importa código do outro, direta ou indiretamente |
| Compartilhamento de Models | SQLAlchemy models do backend nunca são importados ou reimplementados por referência no Worker |
| Compartilhamento de Schemas | Pydantic schemas do backend nunca são importados pelo Worker — se o Worker precisa de uma estrutura de dados equivalente (ex.: o payload da Submissão de Resultados, Seção 9), ela é definida de forma independente do lado do Worker, mesmo que isso duplique campos |
| Compartilhamento de Services | Nenhuma lógica de `app/services/*` do backend é chamada ou importada pelo Worker |
| Compartilhamento de configurações | `Settings`/`.env`/arquivos de configuração não são compartilhados — cada lado define e lê sua própria configuração |
| Compartilhamento de banco de dados | O Worker nunca abre conexão com o PostgreSQL do backend, nunca usa o SQLAlchemy do backend, nunca lê ou escreve tabelas diretamente |
| Compartilhamento de ambiente virtual | `goalkeeper_ai_worker/` tem `requirements.txt` e ambiente Python próprios, nunca instalados no mesmo venv do backend |

## Contratos públicos (únicos canais de comunicação permitidos)

Toda comunicação entre Backend e Worker ocorre exclusivamente por:
- **REST API** — Worker API do backend, autenticada por API Key (Seção 9)
- **Redis** — fila `processing_jobs` e Lock distribuído por vídeo (Seções 2 e 4)
- **Cloudflare R2** — via URLs assinadas de download/upload, nunca credenciais mestras (Seção 9)

Nenhum outro canal é permitido: sem arquivo compartilhado em disco, sem variável de ambiente compartilhada, sem IPC local, sem acesso direto a processo.

## Processo de exceção

Nenhuma exceção às proibições acima é permitida sem uma ADR aprovada, seguindo o mesmo formato desta Constituição (Contexto/Problema/Alternativas/Vantagens/Desvantagens/Decisão/Impacto). Uma exceção implementada sem ADR correspondente é, por definição, uma violação arquitetural — nunca uma decisão válida por si só.

---

# Frozen Architecture

As regras abaixo são consideradas oficiais e não devem ser reabertas sem uma nova revisão arquitetural formal:

- ✓ Worker nunca acessa o banco diretamente.
- ✓ Backend é a única autoridade sobre regras de negócio e sobre a atribuição de versão da Analysis.
- ✓ Toda comunicação Worker↔Backend acontece via API (HTTP + API Key) — nunca acesso direto a Postgres ou uso de credenciais mestras do R2.
- ✓ Redis é a fila oficial (Streams, consumer group) e também a base do Lock de vídeo e do heartbeat.
- ✓ Plugins seguem o Plugin Registry único — nenhuma família tem mecanismo próprio divergente.
- ✓ Modelos seguem o Model Registry, especialização do Plugin Registry.
- ✓ `video_id` é o Correlation ID oficial; `job_id` representa apenas uma tentativa de processamento.
- ✓ Analysis nunca é sobrescrita — cada execução bem-sucedida gera uma nova versão.
- ✓ Toda Analysis carrega proveniência completa: Pipeline Version, Worker Version, Model Versions, Schema Version.
- ✓ Toda submissão de resultados ao backend é idempotente (duas fases).
- ✓ Worker é stateless entre Jobs — único estado local é o checkpoint efêmero do Job em andamento.
- ✓ Nenhum Job inicia processamento sem antes adquirir o Lock do vídeo correspondente.
- ✓ Todo Stage possui timeout e classificação de retry (transitório/permanente) definidos.
- ✓ Cancelamento é sempre gracioso — nunca ocorre no meio de uma operação não interrompível com segurança.
- ✓ Nenhum Plugin roda sem estar explicitamente habilitado em configuração.
- ✓ **Compartilhar o mesmo repositório Git não autoriza compartilhamento de runtime, dependências, código Python, banco de dados ou lógica de negócio** (ADR-009).
- ✓ Qualquer `import` entre `backend_fastapi/` e `goalkeeper_ai_worker/`, em qualquer direção, é uma violação arquitetural — o Worker é tratado como se estivesse em outro repositório, mesmo residindo no mesmo Git.
- ✓ Toda comunicação Backend↔Worker passa exclusivamente pelos três contratos públicos (REST API, Redis, Cloudflare R2) — ver seção "Boundary Enforcement" para a lista completa de proibições e o processo obrigatório de exceção via ADR.
