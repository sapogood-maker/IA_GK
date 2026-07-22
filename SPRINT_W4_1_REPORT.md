# SPRINT_W4_1_REPORT.md — Sprint W4.1: Alinhamento Arquitetural

> Sprint exclusivamente de sincronização documental. Nenhuma funcionalidade nova, nenhuma linha de OpenCV/YOLO/MediaPipe/OpenPose/OCR/GPU/CUDA/ROCm/TensorRT/VideoReader/FrameProvider/Scheduler/Retry/Heartbeat/Multi-GPU foi escrita. Pipeline, InferenceEngine, Registry, Workspace, BackendClient, Redis, Lock, Storage e Tests não foram modificados.

## 1. Arquivos alterados

**Apenas um arquivo de código foi tocado, e só documentação:** nenhum. Confirmo explicitamente: **zero arquivos em `worker/` ou `tests/` foram alterados nesta sprint.**

Arquivo de documentação alterado:
- `AI_WORKER_CONSTITUTION.md` — reescrita de: cabeçalho/premissas, Seção 1 (tabela de módulos), Seção 2 (Pipeline e Stages, dividida em 2.1 "fluxo real" e 2.2 "visão original ainda não implementada"), Seção 6 (status do Plugin Registry), novas Seções 6.1 (Camada de Inferência) e 6.2 (PipelineState e Workspace), nota em Seção 8, Seção 12 (árvore do repositório), Seção 13 (Roadmap — W2/W3/W4 marcadas concluídas, W5 redefinida), novo item 10 em Riscos Arquiteturais, nova Seção 15 ("Preparação para Visão Computacional").

Arquivo de documentação criado: `SPRINT_W4_1_REPORT.md` (este arquivo).

## 2. Documentação sincronizada

| O que | Antes (desatualizado) | Depois (sincronizado) |
|---|---|---|
| Seção 1 — módulos | `orchestrator`/`pipeline`/`state`/`workspace`/`events` descritos como vazios (W2.1); `inference/` não existia no documento | Todos marcados com status real (✓ Implementado / Vazio-aspiracional), incluindo a nota de que `models/`/`registry/`/`gpu/` convergiram para `inference/` na prática |
| Seção 2 — Pipeline | Só a visão original de 14 etapas aspiracionais | 2.1: fluxo real de 10 Stages implementado, com `FakeProcessingStage`/`GenerateArtifactStage` já não mencionados como ativos; 2.2: o que da visão original ainda falta |
| Seção 6 — Plugin Registry | Descrito só como aspiracional | Status explícito: princípio provado (`inference/registry.py`), módulo genérico de topo ainda não extraído — decisão deliberada, não esquecimento |
| Seção 6.1/6.2 (novas) | Não existiam | `InferenceEngine`, `FakeInferenceEngine`, Registry, `engine.py`, Types, Exceptions, `PipelineState`, `WorkspaceManager`, eventos internos — todos documentados com o nome real dos arquivos |
| Seção 12 — árvore | Mostrava `queue/`, `lock/`, `backend_client/` como pastas soltas (já corrigido na W2.1) e nada de `inference/`/`pipeline/stages/` | Árvore conferida arquivo a arquivo contra o disco nesta revisão |
| Seção 13 — Roadmap | W3/W4 sem marca de conclusão; W5 = "Tracking, Métricas, Eventos e Artefatos reais" | W2/W3/W4 marcadas ✓ concluídas (com W4 corrigida: não foi "primeiro modelo real", foi a arquitetura); W2.1/W4.1 adicionadas como sprints de alinhamento; **W5 redefinida** = infraestrutura de leitura de vídeo (escopo antigo empurrado para uma sprint futura, número a definir) |
| Seção 15 (nova) | Não existia | "Preparação para Visão Computacional" — escopo oficial da W5 |

## 3. Auditoria arquitetural

- **`FakeProcessingStage`/`GenerateArtifactStage` como estrutura antiga:** confirmado que não aparecem em nenhum documento de arquitetura vivo (`AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, `DOMAIN_ARCHITECTURE.md`) — só nos relatórios históricos `SPRINT_W3_REPORT.md`/`SPRINT_W4_REPORT.md`, onde é correto que apareçam (são registros datados do que aconteceu naquela sprint, não documentação viva).
- **`queue/`, `lock/`, `backend_client/` como pastas soltas:** confirmado que não aparecem mais em nenhum documento — já haviam sido corrigidas na W2.1 (viraram `infrastructure/redis/{consumer,lock}.py` e `infrastructure/backend_client/`); esta revisão apenas confirmou que a correção se manteve.
- **Divergência real encontrada e agora documentada:** a Seção 6 original previa `models/`+`registry/`+`gpu/` como módulos de topo separados para a camada de IA. A implementação real (W4) consolidou tudo em `worker/inference/`. Isso não é um erro — é uma simplificação razoável e deliberada, mas estava silenciosamente divergente da Constituição até esta revisão. Agora está explicitamente documentado como decisão consciente (Seção 1, linhas `models/`/`registry/`/`gpu/`).
- **Pequeno código morto identificado (não corrigido, por não ser permitido nesta sprint):** o evento `ArtifactGenerated` (`events/events.py`) não é mais emitido por ninguém desde que `GenerateArtifactStage` foi removida — documentado explicitamente na Seção 1, deixado como está.

## 4. Boundary Enforcement

| Verificação | Resultado |
|---|---|
| Import cruzado (`backend_fastapi`, `from app.`, `import app.`) em todo `goalkeeper_ai_worker/**/*.py` | **Zero ocorrências reais** (só a própria regra documentada em `worker/__init__.py`) |
| Dependência de banco (`sqlalchemy`/`psycopg`/`asyncpg`) em código ou `requirements.txt` do Worker | **Zero ocorrências** |
| Referência ao venv do backend (`venv_gk310`) dentro do Worker | **Zero ocorrências** |
| Ambiente de teste usado | `venv_worker310` (próprio) — nunca o do backend |

**Veredito: nenhuma violação de Boundary Enforcement.**

## 5. Estado atual da arquitetura

Consolidado (Seção 1/2/6/6.1/6.2/12 da Constituição, todas sincronizadas nesta sprint):

- **Fundação (W1):** config, logging, ciclo de vida — completos.
- **Comunicação (W2):** Redis, Worker API, R2 (URLs assinadas), Lock — completos.
- **Pipeline de Processamento (W3):** `WorkerOrchestrator`, 10 Stages, `PipelineState`, `WorkspaceManager`, eventos internos — completos.
- **Camada de Inferência (W4):** `inference/` completo e plugável (`InferenceEngine`, `FakeInferenceEngine`, Registry, Types, Exceptions) — comprovadamente trocável por teste automatizado.
- **Ainda aspiracional, sem código:** `gpu/`, Tracker/Metric/Event(técnico)/Artifact/Report Registry, Submissão de Resultados (depende do backend, ADR-008), Retry/Timeout/Cancelamento reais (Seção 5 ainda é só política escrita), checkpoint durável entre máquinas, heartbeat, observabilidade avançada.

## 6. Checklist de preparação para a W5

- [x] Contrato `InferenceEngine.process(state)` estável e testado — nenhuma mudança nele é necessária para a W5.
- [x] `PipelineState` já tem `download_path` (onde o vídeo baixado mora) e `inference_result` (onde um resultado real vai ser registrado).
- [x] `FrameMetadata` (tipo) já existe em `inference/types.py`, hoje zerado — pronto para receber valores reais.
- [x] `WorkspaceManager` já garante um diretório isolado por Job onde um `VideoReader` pode operar sem conflito entre Jobs concorrentes.
- [x] Nenhuma Stage do Pipeline decodifica vídeo — a responsabilidade de abrir/ler frames é livre para ser desenhada do zero na W5, sem depender de nada que já exista incorretamente.
- [ ] **Decisão em aberto (não bloqueante):** `VideoReader`/`FrameProvider`/`FrameIterator` vivem dentro de `worker/inference/` ou num módulo irmão novo (`worker/video/`) — fica para o início da W5, registrado na Seção 15.

## 7. Confirmação explícita

**A arquitetura do Goalkeeper AI Worker está pronta para iniciar a Sprint W5** (`VideoReader`, `FrameProvider`, `FrameIterator`, `FrameMetadata` real). Esta sprint (W4.1) encerra oficialmente a fase de Arquitetura: `AI_WORKER_CONSTITUTION.md` reflete, seção por seção, exatamente o que existe hoje em `goalkeeper_ai_worker/`, com toda divergência anterior (silenciosa) tornada explícita. Nenhuma decisão pendente bloqueia o início da infraestrutura de leitura de vídeo — a única questão em aberto (onde esse código mora) é de baixo risco e não depende de nenhuma mudança adicional de arquitetura.
