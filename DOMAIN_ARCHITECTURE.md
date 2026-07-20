# DOMAIN_ARCHITECTURE.md — Multi-tenancy, Autorização e Modelo de Dados

> Documento vivo, atualizado na Sprint 5. Complementa `AI_WORKER_ARCHITECTURE.md` (arquitetura do futuro AI Worker) e `PROJECT_ANALYSIS.md` (estado geral do projeto). Este documento descreve **como o backend está organizado hoje** para autenticação, autorização e dados — a base sobre a qual o AI Worker vai operar no futuro, sem precisar alterá-la.

---

## 1. Modelo de autorização

### 1.1 Papéis (`UserRole`)

| Papel | Escopo de acesso |
|---|---|
| `SYSTEM_ADMIN` | Acesso total: todos os clubes, cria novos clubes, gerencia usuários, configurações globais e diagnósticos do sistema (R2) |
| `CLUBE` | Exclusivamente os dados do próprio clube |
| `TREINADOR` | Exclusivamente os dados do próprio clube |
| `ANALISTA` | Exclusivamente os dados do próprio clube |

Só `SYSTEM_ADMIN` enxerga mais de um clube. Não existe (nesta sprint) suporte a um usuário pertencer a vários clubes — se isso for necessário no futuro, a extensão recomendada é uma tabela de associação (`UserClub`/`ClubMembership`), sem alterar o restante do modelo de autorização.

### 1.2 Tenant (`User.club_id`)

Cada usuário tem um `club_id` (nulo somente para `SYSTEM_ADMIN`, obrigatório para os demais — reforçado por uma `CHECK CONSTRAINT` no banco: `role = 'system_admin' OR club_id IS NOT NULL`). Esse campo é a fronteira de isolamento de todo o sistema.

### 1.3 Bootstrap do primeiro administrador

Não existe fluxo de convite/promoção nesta sprint. **O primeiro usuário registrado no sistema (tabela `users` vazia) vira `SYSTEM_ADMIN` automaticamente**, independente do papel pedido no cadastro. A partir do segundo usuário em diante:
- Ninguém pode se autopromover a `SYSTEM_ADMIN` via `/auth/register` (rejeitado com 400).
- `club_id` passa a ser obrigatório e precisa referenciar um clube já existente.

### 1.4 Como a autorização é aplicada (`app/core/authorization.py`)

Módulo separado de `app/core/security.py` (que só cuida de **autenticação** — quem é o usuário). `authorization.py` decide **o que esse usuário pode acessar**:

- `require_roles(*roles)`: dependência que bloqueia (`403`) quem não tiver um dos papéis informados. Usada em ações restritas (ex.: `POST /clubs` só para `SYSTEM_ADMIN`).
- `is_admin(user)` / `effective_club_scope(user)`: `SYSTEM_ADMIN` não tem restrição; qualquer outro papel é limitado ao próprio `club_id`.
- `resolve_club_id_for_*(db, id)`: como `TrainingSession`, `Video` e `ProcessingJob` não têm `club_id` direto, essas funções resolvem o clube dono do recurso através de *joins* explícitos (`Video → TrainingSession → Goalkeeper → Club`), evitando depender de *lazy loading* de relacionamento em sessão assíncrona (que quebraria com `MissingGreenlet`).

Cada router aplica a autorização em três frentes:
1. **Criação**: valida que o `club_id` do recurso sendo criado bate com o `club_id` do usuário (ou que o usuário é admin).
2. **Listagem**: usuários não-admin recebem só os recursos do próprio clube (o parâmetro de filtro `club_id` da query, quando existe, é ignorado para não-admins — sempre prevalece o clube do próprio usuário).
3. **Leitura/edição/remoção por id**: busca o recurso (404 se não existir) e só então valida a posse (403 se for de outro clube).

### 1.5 Endpoints restritos a `SYSTEM_ADMIN`

- `POST /api/v1/clubs` (criar um clube = dar onboarding a um novo tenant)
- `GET /api/v1/users` (listar todos os usuários do sistema — antes acessível a qualquer autenticado, achado de segurança já registrado no `PROJECT_ANALYSIS.md`)
- `GET /api/v1/r2/health` e `POST /api/v1/r2/test-upload` (diagnóstico de infraestrutura, não é dado de tenant)
- `POST /api/v1/coaches` restrito a `SYSTEM_ADMIN` ou `CLUBE` (do próprio clube)

---

## 2. Modelo de dados

### 2.1 Entidades operacionais (já existiam antes desta sprint)

```
User (club_id) ──┐
                  ├──< Coach
Club ─────────────┼──< Goalkeeper ──< TrainingSession ──< Video ──< ProcessingJob
                  └──< Coach
```

### 2.2 Entidades de IA (novas nesta sprint — tabelas vazias, sem nenhum endpoint ainda)

```
ProcessingJob (1) ──── (1) Analysis (versionada: v1, v2, v3...)
                                │
                                ├──< Event (evento tecnico detectado)
                                │       └──< Artifact (clipe/thumbnail daquele evento)
                                ├──< Metric (metrica quantitativa)
                                └──< Artifact (artefato da analise inteira: heatmap, predicoes em lote)

Goalkeeper ──< Report (relatorio agregando analises ao longo do tempo)
```

- **`Analysis`**: uma versão de análise de IA sobre um `Video`. **Nunca é sobrescrita** — cada novo processamento do mesmo vídeo cria uma linha nova com `version` incrementado, preservando o histórico completo. `UniqueConstraint(video_id, version)` garante que não existam duas análises com a mesma versão para o mesmo vídeo. Liga 1:1 com o `ProcessingJob` que a gerou.
- **`Event`**: um evento técnico detectado (tipo, timestamp, confiança) dentro de uma `Analysis`.
- **`Metric`**: uma métrica quantitativa (nome/valor/unidade) de uma `Analysis` — formato genérico para suportar métricas futuras sem precisar de nova migration.
- **`Artifact`**: arquivo gerado (thumbnail, clipe, heatmap) **ou um lote de predições brutas por frame**, sempre armazenado no R2 e referenciado aqui — nunca como linhas individuais no Postgres (evita gerar milhares/milhões de linhas por vídeo). Pode pertencer à análise inteira (`event_id` nulo) ou a um evento específico.
- **`Report`**: relatório agregando uma ou mais análises de um goleiro ao longo do tempo.

**Por que essas tabelas não têm `club_id` próprio**: o isolamento por tenant é herdado transitivamente pela mesma cadeia já usada para os dados operacionais (`Analysis → Video → TrainingSession → Goalkeeper → Club`; `Report → Goalkeeper → Club`). Isso é compatível com `AI_WORKER_ARCHITECTURE.md`, seção 12: o futuro AI Worker nunca precisa saber o que é "clube" — ele só processa por `job_id`/`video_id`, e o backend resolve o tenant sozinho quando necessário.

### 2.3 Status oficiais do pipeline (`ProcessingJobStatus`)

`QUEUED → DOWNLOADING → PREPROCESSING → INFERENCE → POSTPROCESSING → GENERATING_REPORT → UPLOADING_RESULTS → COMPLETED / FAILED / CANCELLED`

Usado por `ProcessingJob.status` e `Analysis.status` — o mesmo vocabulário, reutilizado nas duas entidades. `Video.upload_status` continua com seu próprio enum menor (`PENDING/UPLOADED/PROCESSING/COMPLETED/FAILED`), pois representa um conceito diferente: se o **arquivo** chegou ao R2, não o andamento do **pipeline de IA**.

Ambos os campos deixaram de ser enum nativo do Postgres e viraram `VARCHAR` (validados na aplicação) — enum nativo exige uma migration a cada novo valor; `VARCHAR` é mais preparado para os estados que o AI Worker ainda vai precisar adicionar no futuro.

---

## 3. Responsabilidade de cada módulo (backend)

| Módulo | Responsabilidade |
|---|---|
| `app/core/security.py` | Autenticação: emissão/validação de JWT, extração do usuário autenticado a partir do header `Authorization: Bearer` |
| `app/core/authorization.py` | Autorização: papéis, isolamento por clube, resolução de posse de recursos |
| `app/core/config.py` | Configuração de ambiente (`Settings`), normalização de `DATABASE_URL` |
| `app/core/r2.py` | Acesso ao Cloudflare R2 (credenciais mestras ficam só aqui) |
| `app/models/models.py` | Entidades do banco (SQLAlchemy) |
| `app/schemas/schemas.py` | Contratos de entrada/saída da API (Pydantic) |
| `app/repositories/repositories.py` | Acesso a dados (queries), incluindo as variantes "por clube" usadas pela autorização |
| `app/services/*.py` | Regras de negócio que envolvem mais de um repositório (ex.: `AuthService` decide bootstrap de admin, `VideoUploadService` orquestra upload + R2 + criação de job) |
| `app/api/v1/*.py` | Endpoints HTTP — aplicam autenticação (router-level) e autorização (por endpoint) antes de delegar aos services/repositories |

---

## 4. Preparação para o AI Worker (sem implementá-lo)

Conforme pedido explicitamente nesta sprint, **nenhuma linha do Worker foi criada**. O que já está pronto para quando ele existir:

- Tabelas `analyses`/`events`/`metrics`/`artifacts`/`reports` — vazias, aguardando o Worker popular via API (nunca escrita direta no banco).
- Vocabulário oficial de status (`ProcessingJobStatus`) já reutilizável pelo Worker sem precisar inventar novos nomes.
- Isolamento por tenant já resolvido de forma transitiva — o Worker não precisa carregar nenhum conceito de "clube".
- A autenticação do Worker (API Key + service account, `AI_WORKER_ARCHITECTURE.md` seção 6) continua sendo um mecanismo **separado** do `UserRole` criado nesta sprint — os dois sistemas não se misturam.

---

*Fim do documento.*
