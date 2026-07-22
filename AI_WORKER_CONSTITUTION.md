# AI_WORKER_CONSTITUTION.md — Goalkeeper AI Worker

**Constituição arquitetural oficial do serviço `goalkeeper_ai_worker`, parte do monorepo `IA_GK`.**

> Documento vivo. A revisão original (antes da primeira linha de código) promoveu toda decisão então registrada como "risco em aberto" ou "nota" a arquitetura principal ou a um ADR explícito. **Sprint W2.1** (pós-Sprint W2, `ARCHITECTURE_REVIEW_W2.md`) sincronizou a Seção 1 e a Seção 12 com a estrutura real implementada (`contracts/`, `infrastructure/`, `core/`). **Sprint W4.1** (pós-Sprint W4, `SPRINT_W4_1_REPORT.md`) fez a mesma sincronização para o Pipeline completo (W3) e a camada de Inferência (W4): `orchestrator/`, `pipeline/stages/`, `state/`, `workspace/`, `events/` deixaram de estar vazios, e o módulo `inference/` — não previsto com esse nome na versão original — passou a ser a arquitetura oficial de IA plugável.
>
> **A partir da Sprint W6, não há mais sprints de sincronização (Wx.1).** Documentação passou a fazer parte do Definition of Done de cada sprint — toda alteração arquitetural é registrada aqui durante a própria sprint que a introduz, nunca depois. A revisão da W6 incorporou o que ficou pendente da W5 (`worker/video/`) e o que a W6 introduziu (`BasicVisionEngine`, `frame_ops.py`, configuração de pré-processamento de frame). A revisão da W7 incorporou `inference/processors/` (`FrameProcessor`, `ColorProcessor`/`ResizeProcessor`/`ROIProcessor`/`StatisticsProcessor`, `PipelineProcessor`) — `BasicVisionEngine` deixou de transformar frame diretamente e passou a orquestrar essa pipeline de Processors. A revisão da W8 incorporou `inference/detectors/` (`Detector`, `YOLODetector`, Registry e `factory.py` próprios) e `YOLOProcessor` — o primeiro modelo real de detecção, isolado atrás de uma abstração própria desde o primeiro dia. A revisão da W9 incorporou `inference/trackers/` (`Tracker`, `ByteTrackTracker`, Registry e `factory.py` próprios) e `TrackingProcessor` — o primeiro Tracker real, mais o par `reset()` (`FrameProcessor`/`Tracker`/`PipelineProcessor`) que corrige um vazamento de estado entre Jobs sequenciais, descoberto durante a implementação. **A revisão da W10** incorpora `inference/events/` (`SceneAnalyzer`, `BasicSceneAnalyzer`, Registry e `factory.py` próprios) e `SceneAnalysisProcessor` — a primeira camada de interpretação de cena, ainda sem nenhuma regra de negócio de futebol; reaproveitou a plumbing de `reset()` da W9 sem precisar recriá-la, e corrigiu de curso a expectativa antiga (W4.1) de que um "Event Registry técnico" nasceria dentro de `worker/events/` — em vez disso, materializou-se em `worker/inference/events/`.

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

| Módulo | Status | Responsabilidade | O que NÃO faz |
|---|---|---|---|
| `orchestrator` | ✓ Implementado (W3) | `WorkerOrchestrator`: executa o Pipeline (`process_job`), decide a transição entre Stages, garante `Cleanup`/`ReleaseLock` em bloco `finally`, consome a fila (`run_forever`) | Não decide o conteúdo de nenhum Stage; não conhece motores de inferência específicos |
| `pipeline` | ✓ Implementado (W3/W4) | `stages/`: os 10 Stages ativos hoje — `ReceiveJobStage`, `ValidateJobStage`, `AcquireLockStage`, `PrepareWorkspaceStage`, `DownloadVideoStage`, `InferenceStage`, `UploadArtifactStage`, `UpdateStatusStage`, `CleanupStage`, `ReleaseLockStage` (Seção 2) | Não orquestra a sequência (isso é do `orchestrator`); nenhum Stage conhece OpenCV/YOLO/PyTorch |
| `inference` | ✓ Implementado (W4/W6/W7/W8/W9/W10) — **não previsto com este nome na versão original da Constituição** | Único lugar onde código de visão computacional pode existir: `InferenceEngine` (contrato, Seção 6.1), `BasicVisionEngine` (motor **padrão**, orquestrador fino), `inference/processors/` (`FrameProcessor`s independentes: `ColorProcessor`/`ResizeProcessor`/`ROIProcessor`/`StatisticsProcessor` transformam o frame, `YOLOProcessor` só detecta, `TrackingProcessor` só associa entre frames, `SceneAnalysisProcessor` só interpreta, `PipelineProcessor`, Registry próprio), `inference/detectors/` (Sprint W8 — **API de Detecção**: `Detector`, `YOLODetector`, Registry e `factory.py` próprios), `inference/trackers/` (Sprint W9 — **API de Tracking**: `Tracker`, `ByteTrackTracker`, Registry e `factory.py` próprios), `inference/events/` (Sprint W10, NOVO — **API de Eventos de Cena**: `SceneAnalyzer`, `BasicSceneAnalyzer`, Registry e `factory.py` próprios — base para futuras análises específicas de futebol), `FakeInferenceEngine` (mantido só para testes), `frame_ops.py` (funções puras, chamadas pelos Processors correspondentes), `registry.py` (nome→classe de **motores**) e `engine.py` (`create_engine`, resolve por `WORKER_INFERENCE_ENGINE`) | `Pipeline`/`Orchestrator` nunca importam nada daqui além do contrato `InferenceEngine`; nunca abre um arquivo de vídeo diretamente — sempre via `video/`; nenhum Processor conhece outro Processor; nenhum Processor conhece Ultralytics/pesos/modelos — só os contratos `Detector`/`Tracker`/`SceneAnalyzer`; `Tracker` nunca conhece YOLO/Ultralytics — só o contrato `DetectionResult`; `SceneAnalyzer` nunca conhece ByteTrack/YOLO — só o contrato `TrackingResult` |
| `video` | ✓ Implementado (W5) — **módulo irmão de `inference/`, nunca dentro dele** | `VideoReader` (abre/fecha/valida, via `cv2.VideoCapture` só como biblioteca de leitura), `FrameProvider` (leitura sequencial), `FrameIterator` (protocolo padrão de iterador), `Frame`/`FrameMetadata`/`VideoProperties` (Seção 6.1) | Nenhuma linha de `cv2.dnn`, YOLO, modelo, GPU ou qualquer decisão de pré-processamento (resize/ROI/skip) — isso é responsabilidade da camada de inferência que o consome |
| `contracts` | ✓ Implementado (W2) | Tipos que representam exclusivamente os contratos públicos do Backend — REST (`backend_api.py`) e mensagem do Redis Stream (`queue_message.py`) | Não contém lógica, não importa `app/schemas/schemas.py` do backend (Boundary Enforcement) |
| `infrastructure/redis` | ✓ Implementado (W2) | Cliente Redis, consumer group do stream `processing_jobs` (ack/claim/retry de mensagens) e Lock distribuído por `video_id` (Seção 4, ADR-001/003) | Não decide o que fazer com o Job nem política de negócio, só entrega/confirma mensagens e coordena acesso |
| `infrastructure/backend_client` | ✓ Implementado (W2) | Cliente HTTP do Worker API: camada genérica de requisição + detalhes do Job, atualização de status, URLs assinadas, Contrato Backend↔Worker (Seção 9) | Não acessa Postgres/R2 diretamente |
| `infrastructure/storage` | ✓ Implementado (W3) | Download/upload REAL via URL assinada (`r2_client.py`) | Não decide quando baixar/subir — quem chama é `DownloadVideoStage`/`UploadArtifactStage` |
| `gpu` | Vazio — aspiracional | Abstração de compute (Seção 7) | Ainda nenhuma linha de código; nenhum Plugin específico será conhecido por aqui |
| `registry` (genérico, cross-família) | Vazio — **o padrão já foi provado**, não o módulo | Seção 6 previa um único mecanismo de Plugin Registry de topo, reaproveitado por todas as famílias. O padrão (nome→classe, registrar/resolver, ativação por configuração) já está provado em `inference/registry.py`, mas ainda escopado só a motores de inferência | Extrair um `worker/registry/` genérico compartilhado é decisão para quando uma **segunda** família (Tracker Registry, W6+) precisar do mesmo mecanismo — evita generalizar a partir de uma única instância |
| `models/` | Vazio — mantido por compatibilidade textual | Seção 6 original previa Plugins de modelo (detecção/pose/segmentação/classificação) aqui, resolvidos por um Model Registry separado. **Na prática (W4), essa responsabilidade convergiu para `inference/`** — motores de inferência (incluindo futuros motores de detecção reais) vivem lá, não aqui | Esta pasta não deve receber código; ver `inference/` |
| `tracking/` | Vazio — **igual a `models/`, decisão já tomada** | Previsto aqui na versão original para Plugins de tracking (Tracker Registry) | **Na prática (W9), essa responsabilidade convergiu para `inference/trackers/`** — mesmo padrão de `models/`→`inference/` (W4): a família de Plugin vive dentro de `inference/`, esta pasta de topo não recebe código |
| `metrics/` | Vazio — aspiracional (W6+) | Plugins de métricas (Metric Registry) | Idem |
| `events/events.py` (eventos internos) | ✓ Implementado (W3), com 1 tipo órfão desde a W4 | `JobStarted`/`VideoDownloaded`/`UploadFinished`/`JobCompleted`/`JobFailed` — eventos de ciclo de vida do Job realmente emitidos hoje, só logging por enquanto (Seção 6.2). `ArtifactGenerated` continua definido mas **não é mais emitido** por ninguém desde que `GenerateArtifactStage` foi removida (W4) — pequeno código morto, sinalizado aqui, não corrigido (sem mudança funcional permitida) | **Não é** `inference/events/` (linha abaixo) — mesmo nome de pasta (`events`) em dois níveis diferentes da árvore, conceitos inteiramente distintos. A ideia original desta revisão (W4.1) de acomodar um futuro "Event Registry técnico" como submódulo AQUI DENTRO de `worker/events/` **não se concretizou assim** — a W10 implementou a API de Eventos de Cena em `worker/inference/events/` em vez disso (mais perto da camada de inferência que a consome). `worker/events/` segue só com `events.py` (ciclo de vida do Job) |
| `artifacts/` | Vazio — aspiracional (W6+) | Plugins de artefatos (Artifact Registry) | Idem |
| `report/` | Vazio — aspiracional | Plugins de relatório (Report Registry) | Não persiste nada — só agrega |
| `submission` | Vazio — aspiracional (depende de ADR-008, backend) | Monta e envia o payload do Contrato Backend↔Worker em duas fases idempotentes (Seção 9) | Não gera dados, só os empacota e envia |
| `state` | ✓ Implementado (W3) | `PipelineState` (Seção 6.2) — todo o estado de um Job em processamento, trocado entre Stages | Não é banco de dados de produção; não é o checkpoint durável entre máquinas (ainda não existe, ver Riscos) |
| `workspace` | ✓ Implementado (W3) | `WorkspaceManager` (Seção 6.2) — cria/limpa o diretório de trabalho temporário por Job, sempre via `tempfile.mkdtemp` | Não decide o que gravar ali — só oferece o espaço; não usa o diretório `goalkeeper_ai_worker/workspace/` da Seção 12 (ver nota lá) |
| `observability` | Parcial — logging pronto (W1), resto aspiracional | Logging estruturado (Correlation ID obrigatório) já funciona; métricas internas, heartbeat, health check ainda não existem | Não decide política de alerta |
| `core` | ✓ Implementado (W1) | Ciclo de vida do processo (inicialização, shutdown gracioso) e hierarquia de exceções própria (`WorkerError` → `ConfigurationError`/`QueueConnectionError`/`BackendUnavailableError`/`BackendRequestError`/`StorageError`/`PipelineError`) | Não contém lógica de negócio nem de infraestrutura externa |
| `config` | ✓ Implementado (W1-W4, crescendo por sprint) | Toda configuração via `.env` (`WorkerSettings`) — inclui `WORKER_INFERENCE_ENGINE` desde a W4 | Não contém lógica de negócio |

**Regra de dependência (Frozen):** `orchestrator`, `pipeline` só dependem de **interfaces**. Adaptadores concretos (`inference/fake_engine.py`, e futuramente `inference/opencv_engine.py`) implementam essas interfaces e são conectados pelo Registry da própria família (hoje: `inference/registry.py`), nunca por import direto do núcleo.

---

## 2. Pipeline e Estágios (Stages)

Cada Stage recebe o `PipelineState` (Seção 6.2) e devolve o `PipelineState` atualizado — nunca dezenas de parâmetros soltos. Nenhum Stage acessa estado global.

### 2.1 Fluxo real, implementado (W3/W4)

```
Redis (consumer group) → WorkerOrchestrator.process_job
  → ReceiveJobStage → ValidateJobStage → AcquireLockStage → PrepareWorkspaceStage
  → DownloadVideoStage → InferenceStage (chama InferenceEngine.process) → UploadArtifactStage
  → UpdateStatusStage → [bloco finally] CleanupStage → ReleaseLockStage → ACK
```

1. **Recepção do Job** (`ReceiveJobStage`) — o `orchestrator` já reivindicou a mensagem (`job_id`, `video_id`) do consumer group Redis; esta Stage busca os detalhes do Job via `backend_client`.
2. **Validação** (`ValidateJobStage`) — confirma que o `video_id` da mensagem bate com o do Job e que ele não está em estado terminal (`COMPLETED`/`FAILED`/`CANCELLED`). Falha aqui é sempre permanente.
3. **Aquisição do Lock** (`AcquireLockStage`) — adquire o Lock distribuído do vídeo (Seção 4) — nenhuma etapa seguinte roda sem o lock.
4. **Preparação do Workspace** (`PrepareWorkspaceStage`) — cria o diretório de trabalho temporário via `WorkspaceManager` (Seção 6.2).
5. **Download** (`DownloadVideoStage`) — obtém a URL assinada e baixa o vídeo original para o workspace.
6. **Inferência** (`InferenceStage`) — delega inteiramente a `InferenceEngine.process(state)` (Seção 6.1). Hoje: `FakeInferenceEngine` (sem IA real) — lê o vídeo baixado, gera um `InferenceResult` mínimo, salva-o como artefato JSON no workspace.
7. **Upload** (`UploadArtifactStage`) — envia os bytes do artefato ao R2 via URL assinada de upload (esquema `artifacts/{video_id}/{job_id}/{filename}`).
8. **Atualização de Status** (`UpdateStatusStage`) — marca o Job como `COMPLETED` (progresso 100%) junto ao backend.
9. **Limpeza** (`CleanupStage`, bloco `finally`) — remove o workspace, se ele chegou a existir — roda mesmo se qualquer etapa anterior falhar.
10. **Liberação do Lock** (`ReleaseLockStage`, bloco `finally`) — libera o Lock, se ele chegou a ser adquirido — roda mesmo se qualquer etapa anterior falhar.

Falha em qualquer etapa 1-8 (exceção `WorkerError`) marca o Job como `FAILED` e ainda assim executa 9-10. Não há retry automático, checkpoint local durável, timeout por Stage nem cancelamento em andamento nesta implementação — ver Seção 5 (política ainda aspiracional) e Riscos Arquiteturais.

### 2.2 Visão original, ainda não implementada (pós-W5)

A sequência completa de 14 etapas originalmente prevista nesta Constituição continua sendo o destino de longo prazo, mas **"Inferência" já deixou de ser aspiracional** — é `InferenceStage`/`InferenceEngine`, real desde a W4. O que falta:

- **Pré-processamento real** de vídeo (normalização de frame rate/resolução) — depende de `VideoReader`/`FrameProvider`/`FrameIterator` (Seção 15, Sprint W5).
- **Tracking**, **Pós-processamento**, **Métricas** (Metric Registry), **Eventos técnicos** (Event Registry — distinto dos eventos internos de ciclo de vida, Seção 6.2), **Artefatos** (Artifact Registry, plural — hoje há só um artefato fixo por Job), **Relatório** (Report Registry) — todos aspiracionais, sem código, sequenciados para depois da W5 (número de sprint a definir quando a infraestrutura de vídeo estiver pronta).
- **Submissão de Resultados** (duas fases, ADR-002/008) — depende do endpoint do backend que ainda não existe (ADR-008).
- **Conclusão formal só após a Submissão** — hoje `UpdateStatusStage` já marca `COMPLETED`, mas sem o conceito de Submissão prévia (porque `Analysis`/`Event`/`Metric` ainda não são gerados).

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

**Um único contrato de Plugin, um único mecanismo de Registry**, reaproveitado por todas as famílias — evita seis padrões ad hoc ligeiramente diferentes. **Status (W10): o princípio está provado na prática cinco vezes** (`inference/registry.py` para motores, desde a W4; `inference/processors/registry.py` para Processors, desde a W7; `inference/detectors/registry.py` para Detectors, desde a W8; `inference/trackers/registry.py` para Trackers, desde a W9; `inference/events/registry.py` para SceneAnalyzers, desde a W10) — **o módulo genérico de topo ainda não foi extraído**, ver nota na Seção 1, linha `registry`, e Risco 10 (Seção 14).

- **Contrato de Plugin:** nome, família, versão, interface de entrada/saída própria da família, ciclo de vida (`init` → `execute` → `teardown`).
- **Plugin Registry:** resolve, para uma família, qual Plugin está ativo (por versão), a partir de configuração. Descoberta automática de Plugins existentes + ativação explícita por configuração (ADR-005) — nenhum Plugin roda sem estar habilitado.
- **Independência entre famílias:** Plugins de famílias diferentes (detecção, pose, segmentação, classificação, tracking, métricas, eventos, artefatos, relatório) não têm dependência de código entre si — só compartilham o contrato de dados produzido/consumido em cada transição do Pipeline (Seção 2). Adicionar uma família nova (ex.: um sétimo tipo de modelo) não altera as demais.

**Especializações do Plugin Registry:**

| Registry | Família | Status | Exemplos de Plugin |
|---|---|---|---|
| **Model Registry** (implementado como `inference/registry.py`) | Motores de inferência | ✓ Implementado (W4/W6) — `FakeInferenceEngine` e `BasicVisionEngine` registrados hoje | YOLO, RT-DETR, Grounding DINO, SAM2, modelo próprio (futuros) |
| **Processor Registry** (implementado como `inference/processors/registry.py`) | Processors de frame (dentro do motor `BasicVisionEngine`) | ✓ Implementado (W7/W8/W9) — `ColorProcessor`/`ResizeProcessor`/`ROIProcessor`/`StatisticsProcessor`/`YOLOProcessor`/`TrackingProcessor` registrados hoje; dict ordenado, ordem de registro = ordem de execução | Futuro `PoseProcessor` (Seção 16) |
| **Detector Registry** (implementado como `inference/detectors/registry.py`) | Detectors de objetos (usados por `YOLOProcessor`, resolvidos via `factory.py`) | ✓ Implementado (W8) — `YOLODetector` registrado hoje | RT-DETR, Grounding DINO, OWLv2 (futuros, Seção 16) |
| **Tracker Registry** (implementado como `inference/trackers/registry.py`) | Trackers de objetos (usados por `TrackingProcessor`, resolvidos via `factory.py`) | ✓ Implementado (W9) — `ByteTrackTracker` registrado hoje | BoT-SORT, DeepSORT, StrongSORT, OC-SORT (futuros, Seção 16) |
| **Scene Analyzer Registry** (implementado como `inference/events/registry.py`) | Analisadores de cena (usados por `SceneAnalysisProcessor`, resolvidos via `factory.py`) | ✓ Implementado (W10) — `BasicSceneAnalyzer` registrado hoje | Futuros analisadores genéricos alternativos (Seção 16) |
| **Metric Registry** | Métricas | Aspiracional (W6+) | Cada calculadora de métrica |
| **Event Registry** (técnico, específico de futebol) | Eventos técnicos de futebol | Aspiracional (W6+) — **distinto** do `Scene Analyzer Registry` acima: este seria uma camada de análise específica (Defesa/Saída/Reposição/1x1/Cruzamento) que **consumiria** `SceneEvent`s genéricos como entrada, não os produz | Defesa, Saída, Reposição, 1x1, Cruzamento |
| **Artifact Registry** | Artefatos | Aspiracional (W6+) | thumbnail, heatmap, timeline, json, vídeo anotado, clipes, csv, parquet |
| **Report Registry** | Relatório | Aspiracional | Relatório técnico detalhado, resumo para treinador, outros formatos de agregação |

Trocar um Plugin (ex.: `FakeInferenceEngine` por um motor real de OpenCV/YOLO) é escrever uma nova classe conforme o contrato da família + registrá-la + apontar o Registry para ela via configuração — zero mudança em `orchestrator`, `pipeline`, ou em qualquer outra família. Já comprovado por teste automatizado (`tests/inference/test_registry.py::test_swapping_the_active_engine_requires_only_registration_and_config`).

---

## 6.1 Camada de Inferência (Implementação Real — Sprint W4/W6/W7/W8/W9/W10)

Módulo `inference/` — único lugar onde código de visão computacional pode existir.

- **`InferenceEngine`** (`base.py`) — classe abstrata (ABC), o contrato único: `name`, `version`, `async def process(state) -> state`. Nenhuma Stage do Pipeline conhece OpenCV/YOLO/ByteTrack/PyTorch — só este contrato. **Não mudou desde a W4** — trocar de motor, reestruturar por completo o que acontece *dentro* dele (W7), introduzir detecção real (W8), tracking real (W9) ou interpretação de cena (W10) nunca exigiu alterar esta interface.
- **`BasicVisionEngine`** (`basic_vision_engine.py`, versão `2.0.0` desde a W7) — **motor padrão** (`WORKER_INFERENCE_ENGINE=basic_vision`). É um **orquestrador fino**: abre o vídeo (`video.VideoReader`), itera frame a frame (`video.FrameProvider`/`FrameIterator`), decide **apenas** se cada frame entra na pipeline (frame-skipping — `WORKER_FRAME_SKIP`), reseta a `PipelineProcessor` no início de cada Job (`self._pipeline.reset()` — ver nota de estado entre Jobs, abaixo) e delega **toda** transformação/detecção/tracking/interpretação de cena a essa `PipelineProcessor` (ver `inference/processors/`, abaixo). Ele mesmo não chama `cv2.cvtColor`/`cv2.resize`/recorte/Ultralytics/ByteTrack algum — só monta o `InferenceResult` final e o artefato JSON, mesclando `context.to_dict()` (métricas por Processor), `pipeline.processor_names` (ordem executada), `context.detections_to_dict()` (W8), `context.tracking_results_to_dict()` (W9) e, desde a W10, `context.scene_events_to_dict()` (eventos de cena acumulados) ao `to_dict()` do resultado. **Nenhum código de detecção/tracking/interpretação/modelo vive aqui** — o motor só lê `context.detections`/`context.tracking_results`/`context.scene_analysis_results` de volta, exatamente como já lia `context.stats` desde a W7.
- **`inference/processors/`** (Sprint W7/W8/W9/W10) — onde toda transformação/detecção/tracking/interpretação de frame realmente acontece; nenhuma fica concentrada em `BasicVisionEngine`.
  - **`base.py`** — `FrameProcessor` (ABC): contrato único `process(frame, metadata, context) -> (frame, metadata, context)` + `is_enabled(settings)` (classmethod) + `reset()` (Sprint W9, concreto com default no-op — ver nota de estado entre Jobs). **Nenhum Processor conhece outro Processor.** `ProcessorStats`/`ProcessorContext` — acumulam tempo de execução e frames processados por Processor (`context.record`), resultados de detecção (`context.add_detection_result`/`context.detections_to_dict()`, W8), resultados de tracking (`context.add_tracking_result`/`context.tracking_results_to_dict()`, W9) e, desde a W10, resultados de análise de cena (`context.add_scene_analysis_result`/`context.scene_events_to_dict()` — este último achata os eventos de TODOS os frames numa lista cronológica única) — genéricos o bastante para qualquer Processor futuro.
  - **`color_processor.py`**/**`resize_processor.py`**/**`roi_processor.py`**/**`statistics_processor.py`** — inalterados desde a W7/W8 (conversão de cor, resize, ROI, observabilidade — ver revisões anteriores desta Constituição).
  - **`yolo_processor.py`** (`YOLOProcessor`, `name="yolo"`, Sprint W8) — **não transforma a imagem, só detecta**: chama `Detector.detect(frame)` (resolvido por `detectors.factory.create_detector`), acumula o `DetectionResult` no contexto. **Nenhuma linha de Ultralytics aqui** — só o contrato `Detector`. `is_enabled` reflete `bool(settings.detector)`.
  - **`tracking_processor.py`** (`TrackingProcessor`, `name="tracking"`, Sprint W9) — **não detecta nem transforma a imagem, só associa**: lê `context.detections[-1]` (o `DetectionResult` que `YOLOProcessor` acabou de produzir para o MESMO frame, mais cedo na mesma execução da pipeline), chama `Tracker.track(detections)` (resolvido por `trackers.factory.create_tracker`), acumula o `TrackingResult` no contexto. Se nenhuma detecção rodou neste frame, é um no-op seguro. **Nenhuma linha de ByteTrack aqui** — só o contrato `Tracker`. `is_enabled` reflete `settings.tracking_enabled and bool(settings.tracker)`. `reset()` delega a `self._tracker.reset()`.
  - **`scene_analysis_processor.py`** (`SceneAnalysisProcessor`, `name="scene_analysis"`, Sprint W10, NOVO) — **não detecta, rastreia nem transforma a imagem, só interpreta**: lê `context.tracking_results[-1]` (o `TrackingResult` que `TrackingProcessor` acabou de produzir para o MESMO frame, mais cedo na mesma execução da pipeline), chama `SceneAnalyzer.analyze(tracking_result)` (resolvido por `events.factory.create_analyzer`), acumula o `SceneAnalysisResult` no contexto. Se nenhum tracking rodou neste frame (`context.tracking_results` vazio — ex.: `TrackingProcessor` desabilitado), é um no-op seguro, não levanta exceção. **Nenhuma linha de ByteTrack/YOLO/regra de negócio de futebol aqui** — só o contrato `SceneAnalyzer`. `is_enabled` reflete `settings.scene_analysis_enabled and bool(settings.scene_analyzer)` — dois interruptores independentes, mesmo padrão de W9. `reset()` delega a `self._analyzer.reset()`.
  - **`registry.py`** — Registry independente do de `inference/registry.py` (engines), `inference/detectors/registry.py` (Detectors), `inference/trackers/registry.py` (Trackers) e `inference/events/registry.py` (SceneAnalyzers): `register_processor`/`get_processor_class`/`available_processors()`. A ordem de registro **define a ordem de execução por padrão** (`color → resize → roi → statistics → yolo → tracking → scene_analysis`) — por isso usa um `dict` comum (preserva ordem de inserção). `SceneAnalysisProcessor` é registrado por último de propósito — interpreta o `TrackingResult` que o tracking acabou de produzir no mesmo frame.
  - **`pipeline.py`** — `PipelineProcessor`: única responsabilidade é **executar** a sequência de Processors habilitados; expõe `processor_names`, `from_settings(settings)` e, desde a W9, `reset()` — chama `processor.reset()` de cada Processor da pipeline, sem saber QUAL deles tem estado (ver nota de estado entre Jobs, abaixo).
- **`inference/detectors/`** (Sprint W8) — a **API de Detecção**: abstração `Detector` (`detect(frame) -> DetectionResult`), independente de qualquer framework/modelo concreto. `YOLODetector` é a primeira implementação. Ver revisão da W8 desta Constituição para detalhes completos.
- **`inference/trackers/`** (Sprint W9) — a **API de Tracking**: abstração `Tracker` (`track(DetectionResult) -> TrackingResult`, + `reset()`), independente de qualquer algoritmo/biblioteca concreto. `ByteTrackTracker` é a primeira implementação. Ver revisão da W9 desta Constituição para detalhes completos.
- **`inference/events/`** (Sprint W10, NOVO) — a **API de Eventos de Cena**: abstração `SceneAnalyzer`, independente de qualquer algoritmo concreto. `BasicSceneAnalyzer` é apenas a primeira implementação — futuras análises específicas de futebol (`GoalkeeperAnalyzer`, `BallAnalyzer`, `DiveAnalyzer`, `SaveAnalyzer`, `GoalAnalyzer`) consumirão `SceneEvent`s produzidos aqui, sem tocar em `SceneAnalysisProcessor`, `PipelineProcessor`, `BasicVisionEngine`, `Detector` ou `Tracker` (ver Seção 16). **Não confundir com `worker/events/`** (pacote de topo, Sprint W3, eventos de ciclo de vida do Job) — famílias de conceito inteiramente distintas, mesmo nome de pasta em níveis diferentes da árvore.
  - **`base.py`** — `SceneAnalyzer` (ABC): contrato único `analyze(tracking_result: TrackingResult) -> SceneAnalysisResult` + `reset()` (concreto, default no-op — inerentemente stateful, mesmo motivo de `Tracker.reset()`). `SceneAnalyzer` **conhece o contrato `TrackingResult`** (a saída de QUALQUER Tracker, não algo específico do ByteTrack) — mesma lógica que permite `Tracker` conhecer `DetectionResult`: consome o CONTRATO de tracking, nunca a implementação concreta que o produziu.
  - **`types.py`** — `SceneEventType` (enum: `track_started`/`track_updated`/`track_lost`/`track_recovered`/`object_entered_frame`/`object_left_frame`/`object_stopped`/`object_moving`/`occlusion_detected` — nenhum específico de futebol), `MotionState` (enum: `unknown`/`moving`/`stopped`), `TrackLifecycle` (enum: `new`/`active`/`lost` — do ponto de vista do SceneAnalyzer, independente do ciclo de vida interno do Tracker), `SceneEvent` (event_type/track_id/frame_index/label/motion_state/lifecycle/related_track_id + `to_dict()`), `SceneStatistics` (total_tracks_observed/active_tracks/lost_tracks/total_events/events_by_type, **cumulativas** — mesmo padrão de `TrackingStatistics`), `SceneAnalysisResult` (lista de `SceneEvent` + frame_index/analyzer_name/analyzer_version/duration_ms/statistics + `to_dict()`).
  - **`context.py`** — `SceneAnalysisContext`/`TrackObservation`: memória interna PRIVADA de uma instância de `SceneAnalyzer` entre chamadas sucessivas a `analyze()` (última posição/estado/movimento conhecidos por `track_id`) — **não é** o `ProcessorContext` do pipeline (que acumula resultados de TODOS os Processors); é o análogo, para Eventos de Cena, do que os `_hit_counts` são para `ByteTrackTracker`. `reset()` limpa `observations`.
  - **`exceptions.py`** — `SceneAnalysisError` → `SceneAnalysisInitializationError`/`SceneAnalysisExecutionError`, ambas de `WorkerError`.
  - **`registry.py`** — `register_analyzer`/`get_analyzer_class`/`available_analyzers()`. Registra `"basic"` hoje.
  - **`factory.py`** — `create_analyzer(nome, settings)`: espelha `trackers/factory.py`; envolve qualquer falha de inicialização numa `SceneAnalysisInitializationError`.
  - **`scene_analyzer.py`** (`BasicSceneAnalyzer`) — primeira implementação real de `SceneAnalyzer`. Deriva eventos comparando o `TrackingResult` do frame atual contra `SceneAnalysisContext`: track_id novo → `TRACK_STARTED`+`OBJECT_ENTERED_FRAME`; track_id que estava `LOST` reaparecendo → `TRACK_RECOVERED`; track_id ativo desaparecendo do frame → `TRACK_LOST`+`OBJECT_LEFT_FRAME`; deslocamento do centro da bbox abaixo/acima de `WORKER_SCENE_MOTION_THRESHOLD_PX` numa transição de estado → `OBJECT_STOPPED`/`OBJECT_MOVING`; IoU entre duas trilhas do MESMO frame acima de `WORKER_SCENE_OCCLUSION_IOU_THRESHOLD` → `OCCLUSION_DETECTED`. **Nota de design documentada honestamente:** com `analyze()` recebendo só um `TrackingResult` (sem dimensões do frame), `OBJECT_ENTERED_FRAME`/`OBJECT_LEFT_FRAME` são emitidos no MESMO momento que `TRACK_STARTED`/`TRACK_LOST` — a única informação disponível sobre "visibilidade" é a própria presença/ausência no `TrackingResult`, não a posição geométrica em relação às bordas do frame real. `reset()` limpa `SceneAnalysisContext` + contadores cumulativos de estatísticas.
- **`FakeInferenceEngine`** (`fake_engine.py`, Sprint W4/W5) — implementação placeholder, mantida **exclusivamente para testes**. Não usa Processors — não faz nenhuma transformação/detecção/tracking/interpretação de frame. Absorve a responsabilidade que, na W3, pertencia a uma `GenerateArtifactStage` separada (removida).
- **`frame_ops.py`** (Sprint W6) — `convert_bgr_to_rgb`, `resize_frame`, `apply_roi`: funções puras, chamadas pelos Processors correspondentes (nunca duplicadas).
- **`registry.py`** (motores) — `register_engine`/`get_engine_class`/`available_engines()`. Registra `"fake"` e `"basic_vision"` hoje. **Distinto** dos Registries de Processors, Detectors, Trackers e SceneAnalyzers — cinco Registries paralelos, um por camada de plugin.
- **`engine.py`** — `create_engine(nome, settings)`: ponto único de resolução, a partir de `WorkerSettings.inference_engine`. Todo motor registrado é construído como `engine_class(settings)` (convenção uniforme de construtor — mesma convenção adotada por Processors, Detectors, Trackers e SceneAnalyzers). Nunca hardcoded no `orchestrator`.
- **`types.py`** — `Detection`, `FrameMetadata`, `RegionOfInterest`, `InferenceMetadata`, `InferenceResult` (+ `to_dict()` para o artefato JSON). Nenhum dicionário solto. **Não depende de `inference/processors/`, `inference/detectors/`, `inference/trackers/` nem `inference/events/`** — a direção de dependência é sempre das camadas mais concretas para esta (a base), nunca o inverso.
- **`exceptions.py`** — `InferenceError` → `EngineInitializationError`/`InferenceExecutionError`, ambas de `WorkerError`. **Distinta** de `detectors/exceptions.py` (`DetectorError`), `trackers/exceptions.py` (`TrackerError`) e `events/exceptions.py` (`SceneAnalysisError`) — cada família de Plugin com sua própria árvore de exceções, todas descendendo de `WorkerError`.

**Estado entre Jobs (achado arquitetural da Sprint W9, reaplicado na W10):** `WorkerOrchestrator.__init__` constrói `InferenceStage(create_engine(...))` **uma única vez**, para todo o ciclo de vida do processo do Worker (`orchestrator.py`) — `BasicVisionEngine`/`PipelineProcessor`/cada `FrameProcessor` (incluindo `TrackingProcessor`/`ByteTrackTracker` e, desde a W10, `SceneAnalysisProcessor`/`BasicSceneAnalyzer`) são, portanto, **reaproveitados entre Jobs sequenciais**, não recriados por Job. Isso nunca importou para Processors sem estado (Color/Resize/ROI/Statistics/YOLO), mas tanto `Tracker` quanto `SceneAnalyzer` são inerentemente stateful: sem intervenção, a mesma instância vazaria identidade de trilhas/observações de um vídeo para o próximo. **Corrigido, uma única vez, de forma genérica** com o par `FrameProcessor.reset()`/(`Tracker`|`SceneAnalyzer`).`reset()` (ambos concretos, default no-op) + `PipelineProcessor.reset()` (chama `reset()` de cada Processor) + `BasicVisionEngine.process()` chamando `self._pipeline.reset()` no início de cada Job. A W10 **não precisou reinventar esse mecanismo** — só implementou `SceneAnalysisProcessor.reset()`/`BasicSceneAnalyzer.reset()` reaproveitando a plumbing já existente desde a W9, confirmando que o padrão genérico funcionou. Validado por teste automatizado (`test_engine_resets_tracker_state_between_jobs`, W9; `test_engine_resets_scene_analyzer_state_between_jobs`, W10).

**Configuração (todas opcionais):** `WORKER_FRAME_SKIP`, `WORKER_ENABLE_RESIZE`/`WORKER_TARGET_WIDTH`/`WORKER_TARGET_HEIGHT`, `WORKER_ENABLE_ROI`/`WORKER_ROI_X`/`WORKER_ROI_Y`/`WORKER_ROI_WIDTH`/`WORKER_ROI_HEIGHT`, `WORKER_ENABLE_COLOR_PROCESSOR`, `WORKER_ENABLE_STATISTICS_PROCESSOR`, `WORKER_DETECTOR`/`WORKER_MODEL_PATH`/`WORKER_CONFIDENCE_THRESHOLD`/`WORKER_IOU_THRESHOLD`, `WORKER_TRACKER`/`WORKER_TRACKING_ENABLED`/`WORKER_TRACK_MIN_CONFIDENCE`/`WORKER_TRACK_MAX_AGE`/`WORKER_TRACK_MIN_HITS`, `WORKER_SCENE_ANALYZER`/`WORKER_SCENE_ANALYSIS_ENABLED`/`WORKER_SCENE_MOTION_THRESHOLD_PX`/`WORKER_SCENE_OCCLUSION_IOU_THRESHOLD` — todas lidas por `WorkerSettings`, cada uma consultada pelo `is_enabled()` do Processor correspondente (ou, no caso do frame-skip, diretamente pelo engine).

**Artefato JSON:** ao `to_dict()` de `InferenceResult`, `BasicVisionEngine` acrescenta: `"processors"`/`"processor_order"` (W7), `"detection_results"` (W8), `"tracking_results"`/`"tracking_engine"`/`"tracking_statistics"`/`"tracking_time_ms"` (W9) e, desde a W10, `"scene_events"` (saída de `context.scene_events_to_dict()` — TODOS os eventos de TODOS os frames, achatados numa única lista cronológica, não agrupados por frame), `"scene_statistics"` (as estatísticas cumulativas do ÚLTIMO `SceneAnalysisResult`, mesmo padrão de `tracking_statistics`) e `"scene_processing_time_ms"` (lido de `context.stats["scene_analysis"].total_time_ms`, sem duplicar lógica). Um Processor desabilitado simplesmente não aparece em nenhuma das chaves.

**Integrar um novo Processor de transformação (ex.: um futuro `PoseProcessor`):** escrever `XProcessor(FrameProcessor)` em `inference/processors/`, registrá-lo, habilitá-lo por `is_enabled()`/config — **sem alterar** `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator` ou `VideoReader`.

**Trocar o Detector ativo (ex.: RT-DETR no lugar de YOLO):** escrever `XDetector(Detector)` em `inference/detectors/`, registrá-lo, apontar `WORKER_DETECTOR=x` — **sem alterar** `YOLOProcessor`, `PipelineProcessor`, `BasicVisionEngine`, `VideoReader`, `WorkerOrchestrator`, Redis, Backend ou R2. Comprovado por teste automatizado (`tests/inference/detectors/test_factory.py`).

**Trocar o Tracker ativo (ex.: BoT-SORT/DeepSORT/StrongSORT/OC-SORT no lugar de ByteTrack):** escrever `XTracker(Tracker)` em `inference/trackers/`, registrá-lo, apontar `WORKER_TRACKER=x` — **sem alterar** `TrackingProcessor`, `PipelineProcessor`, `BasicVisionEngine`, `VideoReader`, `WorkerOrchestrator`, `Detector`, `YOLOProcessor`, Redis, Backend ou R2. Comprovado por teste automatizado (`tests/inference/trackers/test_factory.py`).

**Construir uma análise específica de futebol (ex.: `GoalkeeperAnalyzer`/`BallAnalyzer`/`DiveAnalyzer`/`SaveAnalyzer`/`GoalAnalyzer`, Sprint W11+):** consumir `SceneEvent`s (via `context.scene_analysis_results`/artefato `"scene_events"`) — **sem alterar** `PipelineProcessor`, `BasicVisionEngine`, `Detector` ou `Tracker` (ver Seção 16). A escolha entre "novo `SceneAnalyzer`" (interpretando `TrackingResult` diretamente) ou "novo Processor que consome `SceneEvent`s" (interpretando um nível acima, a saída de `BasicSceneAnalyzer`) é decisão da própria sprint que a implementar.

## 6.2 Estado do Pipeline e Workspace (Implementação Real — Sprint W3)

- **`PipelineState`** (`state/pipeline_state.py`) — todo o estado de um Job em processamento, passado de Stage em Stage: `job_id`, `video_id`, `message_id`, `started_at`, `job` (`JobDetails`), `workspace_dir`, `download_path`, `artifact_path`, `inference_result`, `lock_acquired`, `status`, `finished_at`, `errors`.
- **`WorkspaceManager`** (`workspace/manager.py`) — `create(job_id)`/`cleanup(dir)`, sempre via `tempfile.mkdtemp` (nunca caminho hardcoded), garantindo isolamento entre Jobs mesmo na mesma máquina. Usa o diretório temporário do sistema operacional, **não** o `goalkeeper_ai_worker/workspace/` citado na Seção 12 — decisão deliberada para cumprir literalmente "sempre tempfile" (`SPRINT_W3_REPORT.md`).
- **Eventos internos** (`events/events.py`) — `JobStarted` (em `ReceiveJobStage`), `VideoDownloaded` (em `DownloadVideoStage`), `UploadFinished` (em `UploadArtifactStage`), `JobCompleted`/`JobFailed` (no `orchestrator`, conforme o desfecho) são os realmente emitidos hoje. `ArtifactGenerated` continua definida mas órfã — era específica da extinta `GenerateArtifactStage` (ver Seção 1). Só logging por enquanto; `video_id`/`job_id` sempre presentes (Correlation ID, Seção 3). **Correção de curso (Sprint W10):** a expectativa original (fechada na revisão W4.1) de acomodar um futuro Event Registry técnico como submódulo AQUI DENTRO de `worker/events/` **não se concretizou assim** — a API de Eventos de Cena (Seção 6.1) foi implementada em `worker/inference/events/`, mais perto da camada de inferência que a consome. `worker/events/` permanece só com `events.py`.

## 6.3 Infraestrutura de Leitura de Vídeo (Implementação Real — Sprint W5)

Módulo `video/` — **irmão** de `inference/`, nunca dentro dele. Resolve a questão que a Seção 15 original deixou em aberto ("onde `VideoReader` mora"): aqui, separado da camada de IA, reutilizável por qualquer motor presente ou futuro.

- **`VideoReader`** (`reader.py`) — abre (`cv2.VideoCapture`, só como biblioteca de leitura — nunca `cv2.dnn`), valida (rejeita `frame_count`/`fps`/dimensões inválidos), expõe `VideoProperties`; suporta `with VideoReader(path) as reader:`.
- **`FrameProvider`** (`provider.py`) — leitura sequencial (`read_next()`); distingue fim normal do vídeo (`None`) de falha real de leitura antes do fim esperado (`FrameReadError`).
- **`FrameIterator`** (`iterator.py`) — protocolo padrão de iterador do Python (`__iter__`/`__next__`, `StopIteration` no fim).
- **`Frame`** (`frame.py`) — a imagem (`numpy.ndarray`, BGR nativo do OpenCV) + `FrameMetadata`.
- **`FrameMetadata`** (`metadata.py`) — posição do frame (`frame_index`/`timestamp_seconds`/`position_seconds`) + propriedades do vídeo de origem, denormalizadas para o `Frame` ser um registro autocontido.
- **`VideoProperties`** (`types.py`) — `fps`/`width`/`height`/`frame_count`/`duration_seconds`, lidas uma única vez na abertura.
- **`exceptions.py`** — `VideoError` → `VideoOpenError` (arquivo inexistente/ilegível) / `InvalidVideoError` (metadados inválidos) / `FrameReadError` (falha de leitura antes do fim esperado), todas de `WorkerError`.

`DownloadVideoStage` salva o vídeo sem extensão (`input_video`) — confirmado empiricamente (Sprint W5) que o OpenCV abre esses arquivos via detecção de conteúdo, então nenhuma mudança foi necessária ali.

---

## 7. Abstração de GPU (Compute Backend)

Interface "Compute Backend": seleção de dispositivo, alocação/liberação de memória e política de fallback resolvidas por um adaptador de compute, nunca espalhadas pelos Plugins de modelo. Hoje: adaptador ROCm (AMD). Futuro: adaptador CUDA. Depois: adaptador CPU (fallback com degradação aceita).

Frameworks de deep learning já abstraem boa parte da diferença ROCm/CUDA no nível de tensor, mas o Worker ainda precisa de uma camada própria para: seleção de dispositivo na inicialização, tamanho de lote adaptativo conforme memória disponível, tratamento de OOM com fallback, e relato de qual dispositivo está em uso (Observabilidade). Nenhum Plugin de modelo, tracker ou Stage do Pipeline verifica diretamente "estou em ROCm ou CUDA?".

**Estado real (Sprint W8/W9):** `YOLODetector` roda sobre `torch` CPU-only (nenhuma dependência de CUDA/ROCm instalada ou usada, por proibição explícita). `ByteTrackTracker` (W9) nem depende de `torch` diretamente — é um algoritmo puro em NumPy (filtro de Kalman + associação por IoU), sem custo de GPU algum. O dispositivo não é escolhido por nenhuma camada própria, é simplesmente o único disponível. Esta seção continua **aspiracional**: nem o primeiro Detector nem o primeiro Tracker reais forçam a existência do Compute Backend, mas o Detector é o primeiro Plugin que de fato se beneficiaria dele (seleção de dispositivo, fallback de OOM) quando GPU for autorizada em sprint futura.

---

## 8. Versionamento e Rastreabilidade Completa

Toda **Analysis** produzida carrega, como metadados de proveniência, as seguintes versões — sem isso não há como auditar retroativamente o que gerou um resultado:

- **Pipeline Version** — identifica a sequência de Stages e o conjunto de Plugins ativos no momento da execução (ADR-006). Versão única por execução do Pipeline inteiro.
- **Worker Version** — versão do software do Worker que processou o Job (distinta do `worker_instance_id`, que identifica só a instância física/processo).
- **Model Versions** — mapa família → versão de cada Plugin de modelo efetivamente usado (Model Registry), persistido por hash de conteúdo dos pesos, não apenas por tag semântica (ADR-007).
- **Schema Version** — versão do contrato de submissão (Seção 9) usado para montar o payload.

Essas quatro versões são obrigatoriamente incluídas no payload da Submissão de Resultados (Seção 9) e devem ser persistidas junto da Analysis correspondente no backend — a exigência de captura é definida aqui; o campo/coluna exato de persistência é uma decisão de schema do backend, fora do escopo deste repositório, mas dependente desta arquitetura.

**Semente real já implementada (W4):** `InferenceMetadata` (Seção 6.1) já captura `engine_name`/`engine_version`/`duration_ms` a cada execução — é o embrião do que se tornará Model Versions quando a Submissão de Resultados existir. Nenhuma mudança de schema foi feita; é só o dado já sendo produzido, ainda sem para onde ser enviado.

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

Árvore real, conferida arquivo a arquivo nesta revisão (W10) contra o disco:

```
IA_GK/                                # monorepo oficial - um unico Git, dois produtos independentes (ADR-009)
├── backend_fastapi/                  # Produto 1: Plataforma SaaS - fora do escopo deste documento
├── frontend_flutter/                 # Produto 1: Flutter Web - fora do escopo deste documento
├── goalkeeper_ai_worker/             # Produto 2: este documento - servico de IA, totalmente independente
│   ├── worker/
│   │   ├── orchestrator/
│   │   │   └── orchestrator.py        # WorkerOrchestrator - process_job, run_forever (Secao 1/2)
│   │   ├── pipeline/
│   │   │   └── stages/                 # os 10 Stages ativos + base.py (interface comum)
│   │   │       ├── receive_job.py, validate_job.py, acquire_lock.py, prepare_workspace.py,
│   │   │       │   download_video.py, inference.py, upload_artifact.py, update_status.py,
│   │   │       │   cleanup.py, release_lock.py
│   │   ├── inference/                  # camada de IA plugavel (Secao 6.1) - NOVO na W4
│   │   │   ├── base.py                  # InferenceEngine (ABC) - o contrato
│   │   │   ├── types.py                  # Detection, FrameMetadata, RegionOfInterest, InferenceMetadata, InferenceResult
│   │   │   ├── exceptions.py              # InferenceError, EngineInitializationError, InferenceExecutionError
│   │   │   ├── frame_ops.py                # convert_bgr_to_rgb/resize_frame/apply_roi - funcoes puras, chamadas pelos Processors (W7)
│   │   │   ├── basic_vision_engine.py       # BasicVisionEngine v2.0.0 - orquestrador fino desde a W7 (delega a PipelineProcessor)
│   │   │   ├── processors/                   # NOVO na W7 - toda transformacao de frame vive aqui, nenhuma no engine
│   │   │   │   ├── base.py                    # FrameProcessor (ABC), ProcessorContext, ProcessorStats
│   │   │   │   ├── color_processor.py          # ColorProcessor - BGR->RGB (delega a frame_ops.convert_bgr_to_rgb)
│   │   │   │   ├── resize_processor.py          # ResizeProcessor - delega a frame_ops.resize_frame
│   │   │   │   ├── roi_processor.py              # ROIProcessor - delega a frame_ops.apply_roi
│   │   │   │   ├── statistics_processor.py        # StatisticsProcessor - so observabilidade, nao transforma
│   │   │   │   ├── yolo_processor.py               # YOLOProcessor (W8) - so detecta, delega a Detector.detect()
│   │   │   │   ├── tracking_processor.py            # TrackingProcessor (W9) - so associa, delega a Tracker.track()
│   │   │   │   ├── scene_analysis_processor.py       # SceneAnalysisProcessor (W10) - so interpreta, delega a SceneAnalyzer.analyze()
│   │   │   │   ├── registry.py                     # register_processor/get_processor_class/available_processors
│   │   │   │   │                                    # (dict ordenado - ordem de registro = ordem de execucao)
│   │   │   │   └── pipeline.py                       # PipelineProcessor - executa a sequencia, from_settings(), reset()
│   │   │   ├── detectors/                     # NOVO na W8 - API de Deteccao, YOLO e so a 1a implementacao
│   │   │   │   ├── base.py                     # Detector (ABC) - detect(frame) -> DetectionResult
│   │   │   │   ├── types.py                     # BoundingBox, ClassLabel, Confidence, Detection, DetectionResult
│   │   │   │   ├── exceptions.py                  # DetectorError, DetectorInitializationError, DetectorExecutionError
│   │   │   │   ├── registry.py                     # register_detector/get_detector_class/available_detectors ("yolo")
│   │   │   │   ├── factory.py                       # create_detector(nome, settings) - resolve por WORKER_DETECTOR
│   │   │   │   └── yolo_detector.py                  # YOLODetector - todo codigo Ultralytics exclusivamente aqui
│   │   │   ├── trackers/                      # NOVO na W9 - API de Tracking, ByteTrack e so a 1a implementacao
│   │   │   │   ├── base.py                     # Tracker (ABC) - track(DetectionResult) -> TrackingResult, reset()
│   │   │   │   ├── types.py                     # TrackId, ClassLabel, Confidence, BoundingBox, TrackState,
│   │   │   │   │                                 # TrackedObject, TrackingStatistics, TrackingResult
│   │   │   │   ├── exceptions.py                  # TrackerError, TrackerInitializationError, TrackerExecutionError
│   │   │   │   ├── registry.py                     # register_tracker/get_tracker_class/available_trackers ("bytetrack")
│   │   │   │   ├── factory.py                       # create_tracker(nome, settings) - resolve por WORKER_TRACKER
│   │   │   │   └── bytetrack_tracker.py               # ByteTrackTracker - reaproveita ultralytics.trackers.byte_tracker,
│   │   │   │                                           # todo codigo especifico de ByteTrack exclusivamente aqui
│   │   │   ├── events/                        # NOVO na W10 - API de Eventos de Cena (NAO e worker/events/, Secao 1)
│   │   │   │   ├── base.py                     # SceneAnalyzer (ABC) - analyze(TrackingResult) -> SceneAnalysisResult, reset()
│   │   │   │   ├── types.py                     # SceneEventType, MotionState, TrackLifecycle, SceneEvent,
│   │   │   │   │                                 # SceneStatistics, SceneAnalysisResult
│   │   │   │   ├── context.py                     # SceneAnalysisContext/TrackObservation - memoria interna do analisador
│   │   │   │   ├── exceptions.py                   # SceneAnalysisError, SceneAnalysisInitializationError/ExecutionError
│   │   │   │   ├── registry.py                      # register_analyzer/get_analyzer_class/available_analyzers ("basic")
│   │   │   │   ├── factory.py                        # create_analyzer(nome, settings) - resolve por WORKER_SCENE_ANALYZER
│   │   │   │   └── scene_analyzer.py                   # BasicSceneAnalyzer - eventos genericos, zero regra de futebol
│   │   │   ├── fake_engine.py                # FakeInferenceEngine - mantido so para testes desde a W6
│   │   │   ├── registry.py                    # register_engine/get_engine_class/available_engines ("fake","basic_vision")
│   │   │   └── engine.py                       # create_engine(nome, settings) - resolve por WORKER_INFERENCE_ENGINE
│   │   ├── video/                       # infraestrutura de leitura de video (Secao 6.3) - NOVO na W5, irmao de inference/
│   │   │   ├── reader.py                 # VideoReader - abre/fecha/valida (cv2.VideoCapture, so leitura)
│   │   │   ├── provider.py                # FrameProvider - leitura sequencial
│   │   │   ├── iterator.py                 # FrameIterator - protocolo padrao de iterador
│   │   │   ├── frame.py                     # Frame (imagem + FrameMetadata)
│   │   │   ├── metadata.py                   # FrameMetadata (video/)
│   │   │   ├── types.py                       # VideoProperties
│   │   │   └── exceptions.py                   # VideoError, VideoOpenError, InvalidVideoError, FrameReadError
│   │   ├── contracts/            # tipos dos contratos publicos do Backend (REST + mensagem do Redis Stream)
│   │   │   ├── backend_api.py     # JobDetails, JobStatusUpdate, PresignedUrl, ArtifactUploadUrlRequest/Response
│   │   │   └── queue_message.py    # JobMessage (job_id, video_id, message_id)
│   │   ├── infrastructure/        # clientes de infraestrutura externa, agrupados por sistema
│   │   │   ├── redis/              # cliente Redis, consumer group (consumer.py), Lock (lock.py, ADR-001/003)
│   │   │   ├── backend_client/      # Worker API: camada HTTP generica (_BaseBackendClient) + endpoints
│   │   │   └── storage/              # r2_client.py - download_to_path/upload_file REAIS via URL assinada
│   │   ├── gpu/                 # vazio - aspiracional (Secao 7)
│   │   ├── registry/            # vazio - o PADRAO ja existe em inference/registry.py (ver Secao 1)
│   │   ├── models/               # vazio - responsabilidade convergiu para inference/ na W4 (ver Secao 1)
│   │   │   ├── detection/, pose/, segmentation/, classification/   # pastas nunca criadas
│   │   ├── tracking/              # vazio - responsabilidade convergiu para inference/trackers/ (W9), igual a models/
│   │   ├── metrics/                # vazio - aspiracional (pos-W5)
│   │   ├── events/
│   │   │   └── events.py             # JobStarted/VideoDownloaded/UploadFinished/JobCompleted/JobFailed (Secao 6.2)
│   │   │                              # NAO e inference/events/ (API de Eventos de Cena, W10) - pastas distintas
│   │   ├── artifacts/                # vazio - aspiracional (pos-W5)
│   │   ├── report/                    # vazio - aspiracional
│   │   ├── submission/                 # vazio - aspiracional (ADR-008, depende do backend)
│   │   ├── state/
│   │   │   └── pipeline_state.py         # PipelineState (Secao 6.2)
│   │   ├── workspace/
│   │   │   └── manager.py                 # WorkspaceManager - tempfile.mkdtemp (Secao 6.2)
│   │   ├── observability/
│   │   │   └── logging_setup.py            # logging estruturado (pronto); metricas/heartbeat/health check (futuro)
│   │   ├── core/
│   │   │   ├── exceptions.py                # WorkerError e toda a hierarquia (Secao 1)
│   │   │   └── lifecycle.py                  # shutdown gracioso
│   │   ├── config/
│   │   │   └── settings.py                    # WorkerSettings - todas as variaveis WORKER_*
│   │   └── main.py                              # so inicializa e delega ao WorkerOrchestrator
│   ├── requirements.txt              # dependencias proprias (opencv-python-headless/numpy - W5; ultralytics - W8,
│   │                                  # traz torch/torchvision CPU-only, sem CUDA/ROCm) - NUNCA compartilhadas com backend_fastapi/
│   ├── pyproject.toml                # metadados do projeto + configuracao do pytest
│   ├── .env.example                  # variaveis documentadas, nenhum valor sensivel real
│   ├── .gitignore                    # .venv/, __pycache__/, /weights/, /workspace/, *.pt (proprio, ancorado, nao o do IA_GK)
│   ├── README.md                     # status da sprint atual, como rodar/testar
│   ├── weights/                       # NAO versionado no git - pesos de modelo; weights/yolo11n.pt (W8) e o
│   │                                   # default de WORKER_MODEL_PATH, baixado automaticamente pela Ultralytics
│   │                                   # no primeiro uso (auto-download por hash/nome, nunca commitado)
│   ├── workspace/                     # NAO versionado no git - diretorio de dados de topo, SEM USO REAL ainda
│   │                                   # (WorkspaceManager usa tempfile.mkdtemp do SO, nao esta pasta - Secao 6.2)
│   ├── docs/                          # (ainda nao criado) documentacao especifica de implementacao do Worker
│   │   ├── architecture/
│   │   └── adr/                       # ADRs de implementacao (ex.: escolha de biblioteca de tracking) -
│   │                                  # distintas das ADRs constitucionais desta Constituicao
│   ├── scripts/                        # (ainda nao criado) utilitarios operacionais (nao Docker, nao IA)
│   └── tests/                          # tests/ (unitarios), tests/pipeline/, tests/inference/, tests/inference/processors/ (W7),
│                                        # tests/inference/detectors/ (W8), tests/inference/trackers/ (W9),
│                                        # tests/inference/events/ (W10) - Detector/Tracker/SceneAnalyzer reais
│                                        # (YOLODetector/ByteTrackTracker/BasicSceneAnalyzer), so a inferencia de
│                                        # outros Processors e mockada quando necessario; tests/video/ (videos reais gerados com OpenCV,
│                                        # nunca mockados); tests/infrastructure/ (Redis real, HTTP mockado)
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
| **W2 — Comunicação** ✓ concluída | Integração com os três contratos públicos do Boundary Enforcement | Redis (consumer group do stream `processing_jobs`), `backend_client` (Worker API, autenticado por API Key), acesso ao R2 via URLs assinadas de download/upload, Lock distribuído por vídeo (ADR-001/003). |
| **(W2.1 — Alinhamento arquitetural)** ✓ concluída | Sincronização documental, sem funcionalidade nova | `contracts/`/`infrastructure/`/`core/` incorporados à Constituição; `QueueConnectionError` corrigida; commit de bootstrap. |
| **W3 — Pipeline de Processamento** ✓ concluída | Orquestração completa do ciclo de um Job, ainda sem IA | `WorkerOrchestrator`, os 10 Stages (Seção 2.1), `PipelineState`, `WorkspaceManager`, eventos internos, download/upload reais. Pipeline "vazio" no lugar da Inferência (`FakeProcessingStage`, depois removida). |
| **W4 — Arquitetura da Camada de Inferência** ✓ concluída | Inferência plugável, ainda sem IA real | Módulo `inference/` completo (Seção 6.1): `InferenceEngine`, `FakeInferenceEngine`, Registry, tipos, exceções. `InferenceStage` substitui `FakeProcessingStage` e absorve `GenerateArtifactStage`. **Não** foi "primeiro modelo real" como esta linha previa originalmente — foi a arquitetura que torna o primeiro modelo real uma troca de Plugin, não uma reescrita. |
| **(W4.1 — Alinhamento arquitetural)** ✓ concluída | Sincronização documental, sem funcionalidade nova | Esta revisão: Seções 1/2/6/12 sincronizadas com W3/W4; Seção 15 (nova) define a W5. Encerra oficialmente a fase de arquitetura do Worker. |
| **W5 — Infraestrutura de Leitura de Vídeo** ✓ concluída | Apenas leitura de vídeo — sem detecção, inferência, IA ou modelos | Módulo `video/` completo (Seção 6.3): `VideoReader`, `FrameProvider`, `FrameIterator`, `FrameMetadata` real (dimensões/fps/contagem de frames/duração de verdade). `FakeInferenceEngine` passou a consumi-lo. Resolvida a questão em aberto da Seção 15 original: `video/` é módulo irmão de `inference/`, nunca dentro dele. |
| **W6 — Primeiro Motor Real de Visão (`BasicVisionEngine`)** ✓ concluída | Camada de visão computacional reutilizável — **ainda sem detecção, YOLO, tracking, classificação ou GPU** | `BasicVisionEngine` (Seção 6.1) — motor **padrão** desde esta sprint; processa frames de verdade (resize/ROI/frame-skip/conversão de cor via `inference/frame_ops.py`, reutilizável por qualquer motor futuro), produz estatísticas básicas. `FakeInferenceEngine` mantida só para testes. **A partir desta sprint, não há mais sprints de sincronização (Wx.1)** — documentação atualizada durante a própria sprint (Definition of Done). |
| **W7 — Pipeline de Processamento de Visão (Processors)** ✓ concluída | Decompor a transformação de frame em Processors independentes — **ainda sem detecção, YOLO, tracking, classificação ou GPU** | `inference/processors/` (Seção 6.1): `FrameProcessor` (contrato), `ColorProcessor`/`ResizeProcessor`/`ROIProcessor`/`StatisticsProcessor`, Registry próprio (ordem de registro = ordem de execução), `PipelineProcessor` (executa a sequência habilitada). `BasicVisionEngine` (v2.0.0) deixa de transformar frame diretamente — vira orquestrador fino que delega tudo à `PipelineProcessor`. Cada Processor habilitável por configuração (`WORKER_ENABLE_*`), sem alterar código. Métricas por Processor entram no artefato (`"processors"`/`"processor_order"`). **Não era mais "primeiro detector real" como esta linha previa originalmente** — foi a arquitetura que torna um futuro `YOLOProcessor` um novo Processor isolado, não uma reescrita do motor. |
| **W8 — Detection API + Primeiro Detector (YOLO)** ✓ concluída | Primeiro modelo real de detecção, por trás de uma abstração própria — **ainda sem tracking, classificação, pose ou GPU** | `inference/detectors/` (Seção 6.1): `Detector` (contrato `detect(frame) -> DetectionResult`), `YOLODetector` (primeira implementação, Ultralytics YOLO11n, CPU-only), Registry e `factory.py` próprios. `YOLOProcessor` (novo Processor, `inference/processors/`) só chama `Detector.detect()` e acumula o resultado no contexto — nenhuma linha de Ultralytics/pesos/modelo fora de `yolo_detector.py`. Habilitável por `WORKER_DETECTOR=yolo`, sem alterar `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator` ou `video/`. Resultados de detecção entram no artefato (`"detection_results"`). |
| **W9 — Tracking API + Primeiro Tracker (ByteTrack)** ✓ concluída | Associar detecções entre frames, por trás de uma abstração própria — **ainda sem classificação, pose ou GPU** | `inference/trackers/` (Seção 6.1): `Tracker` (contrato `track(DetectionResult) -> TrackingResult`, + `reset()`), `ByteTrackTracker` (primeira implementação, reaproveita `ultralytics.trackers.byte_tracker.BYTETracker`, CPU-only), Registry e `factory.py` próprios. `TrackingProcessor` (novo Processor, `inference/processors/`) só chama `Tracker.track()` e acumula o resultado no contexto — nenhuma linha de ByteTrack fora de `bytetrack_tracker.py`. Habilitável por `WORKER_TRACKER=bytetrack` + `WORKER_TRACKING_ENABLED=true`, sem alterar `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `Detector`, `YOLOProcessor` ou `video/`. Resultados de tracking entram no artefato (`"tracking_results"`/`"tracking_engine"`/`"tracking_statistics"`/`"tracking_time_ms"`). **Achado arquitetural corrigido nesta sprint:** a mesma instância de `BasicVisionEngine`/`PipelineProcessor` é reaproveitada entre Jobs sequenciais pelo `WorkerOrchestrator` (construída uma única vez) — sem um `reset()` explícito no início de cada Job, um Tracker stateful vazaria `TrackId`s de um vídeo para o próximo (ver Seção 6.1, "Estado entre Jobs"). |
| **W10 — Scene Events API** ✓ concluída | Primeira camada de interpretação de cena, por trás de uma abstração própria — **ainda sem lógica específica de futebol (defesa/gol/chute), pose, MediaPipe, classificação ou GPU** | `inference/events/` (Seção 6.1): `SceneAnalyzer` (contrato `analyze(TrackingResult) -> SceneAnalysisResult`, + `reset()`), `BasicSceneAnalyzer` (primeira implementação, 9 tipos de evento genérico: `TrackStarted`/`TrackUpdated`/`TrackLost`/`TrackRecovered`/`ObjectEnteredFrame`/`ObjectLeftFrame`/`ObjectStopped`/`ObjectMoving`/`OcclusionDetected`), Registry e `factory.py` próprios. `SceneAnalysisProcessor` (novo Processor, `inference/processors/`) só chama `SceneAnalyzer.analyze()` e acumula o resultado no contexto — zero regra de negócio. Habilitável por `WORKER_SCENE_ANALYZER=basic` + `WORKER_SCENE_ANALYSIS_ENABLED=true`, sem alterar `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `Detector`, `Tracker` ou `video/`. Eventos entram no artefato (`"scene_events"`/`"scene_statistics"`/`"scene_processing_time_ms"`). Reaproveitou, sem alterações, a plumbing de `reset()` entre Jobs já introduzida na W9 (mesma classe de problema: `SceneAnalyzer` também é stateful). |
| **W11 — Primeira Análise Específica de Futebol** | Consumir `SceneEvent`s para produzir a primeira análise com significado de domínio (`GoalkeeperAnalyzer`/`BallAnalyzer`/`DiveAnalyzer`/`SaveAnalyzer`/`GoalAnalyzer` — a definir qual primeiro) | A definir quando a sprint iniciar — a API de Detecção/Tracking/Eventos de Cena já prova o padrão de encaixe (novo Processor +, se necessário, nova família de Registry/factory) repetido três vezes seguidas (W8/W9/W10); a W11 é a primeira vez que a regra de negócio de futebol propriamente dita entra no Worker. |

Itens que continuam arquiteturalmente definidos e congelados (ADRs e Seções correspondentes), mas cujo sequenciamento exato após a W11 será revisado quando ela concluir: Contrato Backend↔Worker (Seção 9, ADR-002/008), Versionamento completo (Seção 8, ADR-006/007), Metric/Artifact/Report Registry (Seção 6), Observabilidade avançada — métricas internas/heartbeat/health check (Seção 11), Escala horizontal (Seção 10).

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
10. **`worker/registry/`, `worker/models/` e `worker/gpu/` seguem vazios enquanto `inference/` concentra tudo** (Seção 1/6.1) — decisão deliberada para não generalizar a partir de uma única família (evita abstração prematura), mas significa que, se uma segunda família de Plugin chegar antes de uma refatoração consciente, há risco de duplicar o padrão em vez de extrair o genérico. Vale revisar quando o Tracker Registry (pós-W7) for implementado.
11. **`create_engine(nome, settings)` (Sprint W6) assume que todo motor registrado aceita `settings` no construtor** — convenção, não imposta por `InferenceEngine` (a ABC não declara `__init__`). Um motor futuro que esqueça esse parâmetro falha só em runtime, na primeira tentativa de `create_engine`, não em tempo de import/definição da classe.
12. **`PipelineProcessor.from_settings()` (Sprint W7) confia que `is_enabled(settings)` de cada Processor não tem efeito colateral e é barata de chamar a cada construção da pipeline** — é um classmethod, não imposto a ser puro pela ABC `FrameProcessor`. Um Processor futuro que faça I/O ou lance exceção dentro de `is_enabled` quebraria a montagem de toda a pipeline, não só a si mesmo. Mesmo risco de convenção-não-imposta do item 11, agora replicado numa segunda família de Plugin (Processors).
13. **`ultralytics` (Sprint W8) traz uma dependência transitiva pesada** (`torch`/`torchvision`, ~700MB, CPU-only nesta sprint) — aceitável para o primeiro Detector real, mas cada Detector futuro (RT-DETR, GroundingDINO, OWLv2) pode trazer seu próprio framework pesado (Transformers, JAX, etc.), sem um mecanismo de dependências opcionais por Detector (`extras_require`) ainda definido. Hoje `requirements.txt` é monolítico — revisitar se o número de Detectors registrados crescer.
14. **`opencv-python-headless` e `opencv-python` (instalado transitivamente por `ultralytics`) colidem no mesmo diretório `cv2/` do site-packages** — ambos os pacotes pip distintos instalam para o mesmo caminho de import. Resolvido nesta sprint fixando `opencv-python-headless==4.10.0.84` (primeira versão com suporte a NumPy 2.x) e reinstalando-a por cima após `pip install ultralytics`; `pip check` reporta permanentemente "ultralytics requires opencv-python, which is not installed" — **falso positivo conhecido e aceito**, não indica quebra real (cv2 importa e funciona; só o metadado do pip não reflete a substituição deliberada por headless). Reprovisionar o ambiente do zero exige repetir esse passo manualmente (documentado em `SPRINT_W8_REPORT.md`) até que um mecanismo mais robusto (ex.: constraints file, ou trocar para `opencv-python` puro) seja adotado.
15. **NumPy 2.x (trazido por `ultralytics`) é uma mudança de versão maior (1.26 → 2.2.6)** — testada e aprovada nesta sprint (117→130 testes, incluindo os de `video/`/`frame_ops.py`, todos passando), mas nenhuma auditoria linha-a-linha de APIs NumPy depreciadas foi feita; risco residual de comportamento sutilmente diferente em código futuro que dependa de detalhes de NumPy 1.x.
16. **`ByteTrackTracker` (Sprint W9) acopla-se a uma API interna, não pública, do pacote `ultralytics`** (`ultralytics.trackers.byte_tracker.BYTETracker`, incluindo o protocolo "results-like" que `_DetectionsAdapter` precisa imitar - `xywh`/`conf`/`cls` + indexação booleana) — decisão pragmática para evitar trazer um pacote `bytetrack`/`lap`/`cython_bbox` separado (historicamente difícil de instalar no Windows), já que `ultralytics` é dependência transitiva desde a W8. Uma atualização de versão do `ultralytics` que renomeie/reestruture esse módulo interno quebraria `bytetrack_tracker.py` silenciosamente até a próxima execução da suíte de testes (não há pin de versão exata além da já existente em `requirements.txt`, e a API interna não segue o mesmo compromisso de estabilidade da API pública `model.track()`).
17. **`WorkerOrchestrator` constrói o `InferenceEngine` (e, por extensão, toda a `PipelineProcessor` e cada `FrameProcessor`) uma única vez, reaproveitando a mesma instância entre Jobs sequenciais** (`orchestrator.py`, Seção 6.1, "Estado entre Jobs") — inofensivo para Processors sem estado, mas qualquer Processor futuro com estado próprio (ex.: um `PoseProcessor` com suavização temporal) precisa lembrar de implementar `reset()` corretamente; nada na ABC `FrameProcessor` força isso além do default no-op, e o próprio `BasicVisionEngine` precisa lembrar de chamar `self._pipeline.reset()` no início de `process()` — convenção, não imposta pelo compilador, mesma classe de risco dos itens 11/12.
18. **`BasicSceneAnalyzer.analyze()` (Sprint W10) recebe apenas `TrackingResult`, sem dimensões do frame** — por isso `OBJECT_ENTERED_FRAME`/`OBJECT_LEFT_FRAME` são emitidos como sinônimos exatos de `TRACK_STARTED`/`TRACK_LOST` (mesma condição, dois nomes), não como eventos geométricos independentes baseados em proximidade das bordas do frame real. Documentado honestamente no código e nesta Constituição (Seção 6.1) - se uma sprint futura precisar da semântica geométrica genuína, `analyze()` precisará receber também a resolução do frame (quebra de contrato, ou um parâmetro opcional adicional).
19. **`SceneStatistics`/`TrackingStatistics` são cumulativas por instância de Analyzer/Tracker, não por Job** — como a mesma instância é reaproveitada entre Jobs (Risco 17) mas `reset()` zera os contadores no início de cada Job, a cumulatividade É por-Job na prática (correta), mas depende inteiramente do `reset()` rodar antes de cada novo vídeo; qualquer falha nesse encadeamento (ex.: uma exceção não tratada entre Jobs que pule o reset) inflaria silenciosamente as estatísticas do próximo vídeo.

---

## 15. Infraestrutura de Visão — Histórico e Decisões (Sprints W5/W6/W7/W8/W9/W10, concluídas)

Esta seção documentava originalmente o escopo *futuro* da W5 (redigida na revisão W4.1); mantida agora como registro das decisões que W5-W10 realmente tomaram, seguindo a regra vigente desde a W6 (sem mais revisões `Wx.1` — o histórico fica aqui, atualizado no lugar).

- **`VideoReader`/`FrameProvider`/`FrameIterator`/`FrameMetadata` real** — implementados na W5 exatamente como planejado, sem desvio (Seção 6.3).
- **Onde o código vive:** decisão fechada na W5 — `worker/video/`, módulo **irmão** de `inference/`, nunca dentro dele (Seção 1, Seção 6.3).
- **Primeiro motor real (`BasicVisionEngine`)** — implementado na W6, consumindo `video/` e introduzindo `inference/frame_ops.py` como camada reutilizável por qualquer motor futuro (Seção 6.1).
- **Decomposição em Processors independentes** — implementada na W7: `inference/processors/` (`FrameProcessor`, `ColorProcessor`/`ResizeProcessor`/`ROIProcessor`/`StatisticsProcessor`, Registry próprio, `PipelineProcessor`). `BasicVisionEngine` deixou de transformar frame diretamente (v1.0.0 → v2.0.0) e passou a orquestrar a execução da pipeline de Processors, mantendo `frame_ops.py` como as únicas funções que de fato tocam pixels (Seção 6.1).
- **Detection API + primeiro Detector real** — implementada na W8: `inference/detectors/` (`Detector`, `YOLODetector`, Registry e `factory.py` próprios) e `YOLOProcessor`. Confirmado na prática o desenho previsto: adicionar detecção real exigiu **apenas** um novo Processor + uma nova família de Registry — zero alteração em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `video/`, Redis, Backend ou R2.
- **Tracking API + primeiro Tracker real** — implementada na W9: `inference/trackers/` (`Tracker`, `ByteTrackTracker`, Registry e `factory.py` próprios) e `TrackingProcessor`. Confirmado na prática o mesmo desenho: adicionar tracking real exigiu **apenas** um novo Processor + uma nova família de Registry — zero alteração em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `Detector`, `YOLOProcessor`, `video/`, Redis, Backend ou R2. **Achado não previsto originalmente:** a W9 revelou que `WorkerOrchestrator` reaproveita a mesma instância de `BasicVisionEngine`/`PipelineProcessor` entre Jobs sequenciais (construída uma única vez, Seção 1) — irrelevante para Processors sem estado (W7/W8), mas exigiu introduzir `FrameProcessor.reset()`/`Tracker.reset()`/`PipelineProcessor.reset()` para que um Tracker stateful não vazasse `TrackId`s de um vídeo para o próximo (Seção 6.1, "Estado entre Jobs"; Risco 17).
- **Scene Events API + primeiro SceneAnalyzer real** — implementada na W10: `inference/events/` (`SceneAnalyzer`, `BasicSceneAnalyzer`, `SceneAnalysisContext`, Registry e `factory.py` próprios) e `SceneAnalysisProcessor`. Terceira repetição consecutiva do mesmo desenho: adicionar interpretação de cena real exigiu **apenas** um novo Processor + uma nova família de Registry — zero alteração em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `Detector`, `Tracker`, `video/`, Redis, Backend ou R2. A W10 **não precisou redescobrir** o problema de estado entre Jobs (Risco 17/W9) — reaproveitou a plumbing `reset()` já existente diretamente, prova de que o mecanismo genérico introduzido na W9 estava corretamente desenhado. Também corrigiu de curso uma expectativa antiga (fechada na W4.1): o "Event Registry técnico" aspiracional, antes previsto como submódulo de `worker/events/`, na prática se tornou a API de Eventos de Cena em `worker/inference/events/` — mais perto da camada que a consome (Seção 1).

## 16. Preparação para a Primeira Análise Específica de Futebol (Sprint W11)

**A W11 ainda não tem escopo definido nesta revisão** (qual análise entra primeiro — `GoalkeeperAnalyzer`/`BallAnalyzer`/`DiveAnalyzer`/`SaveAnalyzer`/`GoalAnalyzer` — a decidir quando a sprint for especificada). O que já está confirmado, pelas três repetições do mesmo padrão em W8 (Detecção), W9 (Tracking) e W10 (Eventos de Cena):

1. Uma nova camada de análise que consome a saída de uma anterior (ex.: um `GoalkeeperAnalyzer` que consome `context.scene_analysis_results`/`"scene_events"` do artefato) só precisa: (a) uma abstração própria, se fizer sentido (`XProcessor` e/ou uma nova família de Registry/`factory.py` em `inference/x/`), (b) registrar o novo Processor por último na ordem de `processors/registry.py`, (c) habilitar via configuração dedicada.
2. **Nenhuma** dessas adições jamais exigiu alterar `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `VideoReader`, Redis, Backend, R2, ou qualquer família de Plugin já existente (Detector/Tracker/SceneAnalyzer permanecem intocados ao adicionar uma nova camada).
3. Se a nova camada for stateful entre frames (como Tracking e Scene Events foram) — lembrar de implementar `reset()` corretamente; a plumbing genérica (`FrameProcessor.reset()`/`PipelineProcessor.reset()`/`BasicVisionEngine.process()` chamando reset no início de cada Job) já existe e não precisa ser recriada (Risco 17).
4. **Diferença real da W11 em relação às anteriores:** pela primeira vez, a lógica introduzida terá semântica de domínio (regras de futebol) em vez de conceitos genéricos de visão computacional — isso não muda a arquitetura de encaixe (Processor + Registry), mas é a primeira sprint em que "regra de negócio" deixa de ser proibida.

**Confirmação explícita:** o projeto está **pronto** para receber a W11, qualquer que seja seu escopo exato — a arquitetura de Processors/Registry/factory já absorveu três camadas de análise real (Detecção, Tracking, Eventos de Cena) sem exigir nenhuma mudança estrutural, só composição.

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
