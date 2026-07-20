# PROJECT_ANALYSIS.md — Goalkeeper AI (IA_GK)

> Relatório técnico de arquitetura, domínio e dívida técnica.
> Baseado exclusivamente no código presente no repositório em 2026-07-20 (branch `main`, commit `6268ba9`).
> Nenhum arquivo de código foi alterado para produzir este relatório.

---

## Sumário Executivo

O projeto **Goalkeeper AI** é uma plataforma de scouting e análise de desempenho de goleiros de futsal/futebol, composta por três partes previstas — **Backend (FastAPI)**, **Frontend (Flutter)** e **AI Worker (visão computacional)** — das quais **apenas o Backend e uma fração do Frontend existem de fato**. O AI Worker, o banco de dados vetorial/RAG, o assistente de IA, os relatórios em PDF, o Telegram e o CI/CD são **apenas documentação de intenção**, sem nenhuma linha de código implementada.

Dois achados críticos merecem atenção imediata (Etapa 7):

1. **Credenciais reais da Cloudflare R2 e um `JWT_SECRET_KEY` estão versionadas no histórico do Git**, inclusive rastreadas no commit `HEAD` sob um nome de arquivo corrompido (`` 1. `backend_fastapi/.env` ``). Ver Etapa 7.1.
2. **O frontend Flutter não compila.** `flutter analyze` acusa 12 erros de compilação (getter `dio` inexistente, imports quebrados). O último commit do histórico, que tinha como objetivo corrigir esse arquivo, é quem introduziu a quebra. Ver Etapa 7.2.

---

## Etapa 1 — Arquitetura Descoberta

### 1.1 Estrutura de diretórios (raiz)

```
IA_GK/
├── backend_fastapi/        # API FastAPI (implementado, funcional em nível de código)
├── frontend_flutter/       # App Flutter (parcialmente implementado, não compila)
├── ai_worker/               # Pasta vazia — Não implementado
├── database/                # Pasta vazia — Não implementado
├── datasets/                 # Pasta vazia — Não implementado
├── infra/                   # Pasta vazia — Não implementado
├── prompts/                  # Pasta vazia — Não implementado
├── docs/                    # Documentação (R2, endpoints Sprint 2B, review Sprint 1)
├── docs_ai_worker_spec.md    # Especificação (aspiracional) do AI Worker
├── docs_architecture_overview.md  # Visão de arquitetura (aspiracional)
├── docs_api_endpoints.md
├── docs_db_schema.sql
├── docs_folder_structure.md  # Estrutura de pastas sugerida (não corresponde 1:1 à atual)
├── docs_implementation_roadmap.md # Roadmap original do projeto (fases)
├── ~30 arquivos .md/.txt na raiz  # Relatórios de sprints/auditorias já concluídos (ver 7.4)
├── .serena/, IA_GK.zip        # Artefatos de ferramentas/backup soltos na raiz (não deveriam estar versionados)
└── .aider.* (chat history, cache) # Resíduos da ferramenta Aider (parcialmente no .gitignore)
```

Não existe `.github/` — **não há pipeline de CI/CD configurado** (Não implementado).

### 1.2 Linguagens e frameworks

| Camada | Linguagem | Framework/lib principais |
|---|---|---|
| Backend | Python 3.11 (Docker) / 3.14 (local) | FastAPI 0.104.1, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, python-jose, passlib[bcrypt], boto3 (R2), asyncpg/psycopg |
| Frontend | Dart / Flutter (SDK ^3.11.0) | go_router 17, dio 5.9, provider 6.1, shared_preferences 2.5 |
| AI Worker | — | Não implementado (documentação menciona YOLO, OpenCV, DeepSORT/ByteTrack, ROCm/ONNX) |
| Infra | Docker / docker-compose | Postgres 16-alpine + backend; sem worker, sem proxy reverso |

### 1.3 Serviços e integrações

- **Banco de dados:** PostgreSQL 16, acessado via SQLAlchemy assíncrono (`asyncpg`).
- **Armazenamento de objetos:** Cloudflare R2 via `boto3` (API S3-compatível), encapsulado em `R2Service` (`app/core/r2.py`).
- **Autenticação:** JWT (HS256) próprio, sem OAuth2/SSO, sem RBAC real (existe apenas um campo `role` textual sem enforcement consistente — ver Etapa 3).
- **Fila de processamento assíncrono / mensageria:** Não implementado (não há Celery, RQ, Redis, RabbitMQ, etc. — o "processing job" é apenas uma linha de tabela criada e nunca atualizada por nenhum worker real).

### 1.4 Docker

Existe **um único** `docker-compose.yml`, dentro de `backend_fastapi/`, definindo:
- `postgres` (porta 5433→5432)
- `backend` (porta 8001, com `--reload`)
- Comentário reservando a porta 8002 para um "AI Worker service" do "Sprint 2" — **nunca implementado**.

Não há compose para o frontend, para um worker de IA, para proxy reverso (nginx/traefik) ou para observabilidade. O `frontend_flutter/Dockerfile` existe isoladamente (build de app web Flutter), mas não está referenciado em nenhum compose.

### 1.5 Arquivos de configuração relevantes

- `backend_fastapi/.env` e `.env.example` — **contêm credenciais reais da Cloudflare R2** (ver Etapa 7.1).
- `backend_fastapi/app/core/config.py` — `pydantic-settings`, valida `database_url` e `jwt_secret_key` (avisa se < 32 chars, mas não bloqueia).
- `frontend_flutter/lib/core/api_config.dart` — URL base fixa (hardcoded) apontando para um host externo (`sslip.io`), sem suporte a múltiplos ambientes (dev/staging/prod).

---

## Etapa 2 — Domínio

### 2.1 Objetivo do sistema (conforme documentado e conforme implementado)

Segundo `README.md` e `docs_architecture_overview.md`: plataforma SaaS para **scouting e análise de desempenho de goleiros de futsal**, usando vídeo + visão computacional para detectar eventos técnicos (defesas, saídas, reposições), permitir validação por treinadores e gerar relatórios.

**O que está de fato implementado hoje é apenas o esqueleto de cadastro e upload**: clubes, treinadores, goleiros, sessões de treino, vídeos e "jobs de processamento" — sem nenhuma análise de IA real acontecendo sobre os vídeos.

### 2.2 Usuários (papéis)

O modelo `User` tem um campo `role: str` livre (default `"viewer"`), mas **não há enforcement de papéis em nenhum endpoint** — qualquer usuário autenticado (ou mesmo não autenticado, ver Etapa 3.3) pode chamar qualquer rota. Os papéis mencionados na documentação aspiracional (`admin`, `club_admin`, `coach`, `viewer`) não têm nenhuma lógica de autorização associada no código atual.

### 2.3 Entidades e relacionamentos (implementado, `app/models/models.py`)

```
User (1) ──< Coach (N)
Club (1) ──< Coach (N)
Club (1) ──< Goalkeeper (N)
Goalkeeper (1) ──< TrainingSession (N)
Coach (1) ──< TrainingSession (N)   [opcional, SET NULL]
TrainingSession (1) ──< Video (N)
Video (1) ──< ProcessingJob (N)
```

- `User`: nome, email (único), hash de senha, `role`.
- `Club`: nome, cidade.
- `Coach`: vínculo 1:1 conceitual entre `User` e `Club` (na prática, nada impede múltiplos `Coach` para o mesmo `user_id`).
- `Goalkeeper`: nome, data de nascimento, mão dominante, altura, peso — sempre vinculado a um `Club`. **Não tem vínculo direto com `User`** (ou seja, não há conceito de "goleiro dono da própria conta").
- `TrainingSession`: título, tipo, data, notas.
- `Video`: metadados de upload + campos de status (`upload_status`) e localização no R2 (`r2_bucket`, `r2_key`, `r2_url`).
- `ProcessingJob`: status (`PENDING/RUNNING/COMPLETED/FAILED`), progresso, contagem de tentativas — **nunca é atualizado por nada além do próprio endpoint CRUD**; não existe worker que consuma esses jobs.

### 2.4 Regras de negócio implementadas

- Senha limitada a 72 bytes (limite do bcrypt) — validada em `AuthService.register`.
- Extensões de vídeo permitidas: `mp4, mov, avi, mkv`; tamanho máximo configurável (`MAX_VIDEO_SIZE_BYTES`, default 500 MB).
- Chave de armazenamento R2 gerada como `videos/{goalkeeper_id}/{ano}/{mês}/{nome_unico}`.
- Criação de `TrainingSession` valida existência do `Goalkeeper` e, se informado, do `Coach`.
- Criação de `Video`/`ProcessingJob` (endpoints legados) valida existência da entidade pai.

### 2.5 Regras de negócio **não implementadas** (apenas documentadas)

- Qualquer lógica de IA (detecção, tracking, classificação de eventos).
- Geração de relatórios (PDF).
- RAG / assistente de IA / busca semântica.
- Notificações via Telegram (existe apenas uma tela estática no frontend).
- Fluxo de correção de eventos por treinador ("coach_corrections").
- Multi-tenancy real / isolamento de dados entre clubes (qualquer usuário lista todos os clubes/goleiros/vídeos do sistema).

---

## Etapa 3 — Inventário do Backend

Localização: `backend_fastapi/app/`.

### 3.1 Endpoints (todos sob prefixo `/api/v1`)

| Router | Método/Rota | Auth exigida? | Observação |
|---|---|---|---|
| `auth.py` | `POST /auth/register` | Não (público, por natureza) | Retorna tokens direto no registro |
| | `POST /auth/login` | Não | |
| | `POST /auth/refresh` | Não | Aceita qualquer refresh token válido, **sem checar revogação** |
| | `GET /auth/me` | **Sim** (única rota protegida do sistema) | via `get_current_user` |
| `users.py` | `GET /users`, `GET /users/{id}` | **Não** | Lista todos os usuários do sistema (nome, email, role) sem autenticação |
| `clubs.py` | `POST/GET /clubs`, `GET /clubs/{id}` | **Não** | |
| `coaches.py` | `POST /coaches`, `GET /coaches/{id}` | **Não** | |
| `goalkeepers.py` | `POST/GET /goalkeepers`, `GET /goalkeepers/{id}` | **Não** | `GET /goalkeepers` sem `club_id` retorna `[]` (hardcoded) em vez de listar todos |
| `training_sessions.py` | `POST/GET/PUT/DELETE` | **Não** | CRUD completo |
| `videos.py` | `POST /videos/upload` (multipart), `GET /videos/{id}/status`, CRUD legado | **Não** | Upload real para R2 funcional em nível de código |
| `processing_jobs.py` | CRUD completo + `GET /{id}/status` | **Não** | Não há nada que efetivamente processe o job |
| `r2.py` | `GET /r2/health`, `POST /r2/test-upload` | **Não** | Endpoints de diagnóstico do bucket R2 — **expõem operação de escrita/leitura no bucket sem autenticação** |

**Achado importante:** de ~30 endpoints, apenas 1 (`/auth/me`) exige autenticação. Todo o restante do CRUD de negócio é publicamente acessível por qualquer cliente que conheça a URL da API.

### 3.2 Models (SQLAlchemy) — ver Etapa 2.3. Estão em um único arquivo `models/models.py` (145 linhas, 7 entidades).

### 3.3 Schemas (Pydantic) — único arquivo `schemas/schemas.py` (227 linhas). Cobre Create/Update/Response para cada entidade. Sem versionamento de schema além do prefixo `v1` da URL.

### 3.4 Serviços

- `AuthService`: registro, login, refresh de token. Gera `access_token` e `refresh_token` mas **o `refresh` retorna o mesmo `refresh_token` recebido** ao invés de rotacioná-lo (`auth_service.py:88`), o que é uma prática de segurança fraca (refresh token de vida longa nunca é invalidado).
- `VideoUploadService`: validação de arquivo, upload para R2, criação de `Video` + `ProcessingJob`. Salva o arquivo temporariamente em disco local (`/tmp` por padrão) antes do upload — funciona, mas não há limpeza garantida em todos os caminhos de exceção (há um `try/except` de limpeza, mas se `temp_path` não foi definido antes da exceção, o bloco `except` quebra ao referenciar `temp_path` não definida — ver Etapa 7.3).
- `R2Service` (`core/r2.py`): wrapper completo sobre boto3 para R2 (upload, delete, presigned URL, health check). Bem estruturado e é o módulo mais maduro do backend.

### 3.5 Autenticação e segurança (`core/security.py`)

- Hash de senha com bcrypt (`passlib`).
- JWT HS256 com `exp`.
- **`hash_password()` contém `print()` de debug que loga a senha em texto puro, seu tipo e tamanho** (`core/security.py:22-27`) — ativo em produção, grava senhas no log/stdout do container. Achado crítico de segurança (ver Etapa 7.1).
- `get_current_user` (em `auth.py`, não em `security.py` — está fora de lugar) decodifica o token e busca o usuário, mas essa dependência **só é usada em `/auth/me`**.

### 3.6 Middlewares

- Apenas `CORSMiddleware`, configurado com `allow_origins=["*"]` **e** `allow_credentials=True` simultaneamente — combinação que a maioria dos navegadores rejeita/ignora silenciosamente por violar a spec de CORS, e que, quando aceita por algum cliente, representa risco de segurança (qualquer origem pode enviar credenciais).
- Não há middleware de logging estruturado, rate limiting, ou tratamento global de exceções.

### 3.7 Migrations (Alembic)

Três migrations, incrementais e coerentes com os models atuais:
1. `001_initial_schema.py` — schema inicial (users, clubs, coaches, goalkeepers, training_sessions, videos, processing_jobs).
2. `002_add_sprint2a_tables.py` — ajustes do "Sprint 2A".
3. `003_add_r2_integration.py` — colunas de integração R2 e enums de status.

Não há testes automatizados de migration (upgrade/downgrade), mas os `downgrade()` estão implementados coerentemente.

### 3.8 Banco de dados

PostgreSQL 16, acesso 100% assíncrono via SQLAlchemy 2.0 + asyncpg. `Base.metadata.create_all` também roda no evento de `startup` do FastAPI (`main.py:38-39`) — **isso é redundante e potencialmente conflitante com o Alembic**: em produção, ter tanto `create_all` automático quanto migrations versionadas é uma prática arriscada (podem divergir).

### 3.9 Testes

`backend_fastapi/tests/` contém **apenas um `__init__.py` vazio**. **Não implementado** nenhum teste automatizado (unitário ou de integração) para o backend. Existe um `test_hash.py` solto na raiz de `backend_fastapi/` (fora da pasta `tests/`), que parece ser um script manual de depuração, não um teste automatizado real.

### 3.10 Dependências (`requirements.txt`)

15 linhas, versões fixadas (bom para reprodutibilidade). Nota: `passlib[bcrypt]==1.7.4` aparece **duas vezes** (linhas 12 e 16) — duplicata inofensiva, mas sinal de arquivo mantido sem cuidado.

---

## Etapa 4 — Inventário do Frontend

Localização: `frontend_flutter/lib/`.

### 4.1 Telas existentes

Todas definidas em um único arquivo monolítico `lib/main.dart` (1803 linhas) — não há pasta `screens/` ou `widgets/` separada, ao contrário do que a própria documentação (`docs_folder_structure.md`) sugere.

| Rota | Tela | Conectada à API? |
|---|---|---|
| `/login` | `LoginScreen` | **Sim** — via `AuthProvider`/`AuthRepository` |
| `/painel` | `PainelScreen` (dashboard) | **Sim** — via `DashboardProvider`/`DashboardRepository`, agrega 6 chamadas (`/videos`, `/processing-jobs` filtrados, `/clubs`, `/training-sessions`) |
| `/clubes` | `ClubesScreen` | **Não** — dados 100% hardcoded (`_ItemSecao('São Paulo FC Sub-20', ...)`) |
| `/goleiros` | `GoleirosScreen` | **Não** — dados hardcoded |
| `/videos` | `VideosScreen` | **Não** — dados hardcoded |
| `/analises` | `AnalisesScreen` | **Não** — dados hardcoded |
| `/sessoes-de-treino` | `SessoesTreinoScreen` | **Não** — dados hardcoded |
| `/relatorios` | `RelatoriosScreen` | **Não** — dados hardcoded |
| `/telegram` | `TelegramScreen` | **Não** — dados hardcoded, funcionalidade inexistente no backend |
| `/usuarios` | `UsuariosScreen` | **Não** — dados hardcoded |
| `/configuracoes` | `ConfiguracoesScreen` | **Não** — dados hardcoded |

Ou seja: **de 11 telas, apenas 2 (login e painel) são funcionais de verdade**; as outras 9 são protótipos visuais estáticos com nomes e números fictícios de exemplo (goleiros "Rafael Monteiro", "Bruna Alves" etc.), sem nenhum botão funcional (`onPressed: () {}` vazio em todos os CTAs dessas telas).

### 4.2 Roteamento

`go_router`, com `redirect` baseado em `AuthProvider.isAuthenticated`. Lógica correta: redireciona para `/login` se não autenticado, e de `/login`/`/` para `/painel` se já autenticado.

### 4.3 Gerenciamento de estado

`provider` (`ChangeNotifier`) — dois providers registrados globalmente (`AuthProvider`, `DashboardProvider`) e um terceiro (`GoalkeeperProvider`) **implementado mas nunca registrado no `MultiProvider` nem usado em nenhuma tela** — código morto.

### 4.4 Integração com API — **quebrada (não compila)**

`flutter analyze` executado neste repositório retorna **12 erros de compilação**:

```
error - The getter 'dio' isn't defined for the type 'ApiClient'
  (auth_repository.dart:18,31,39,48 · dashboard_repository.dart:37 · goalkeeper_repository.dart:10,23,36)
error - Target of URI doesn't exist: 'core/api_config.dart'  (services/api_client.dart:2)
error - Undefined class 'SessionService'                      (services/api_client.dart:25)
error - Undefined name 'ApiConfig'                             (services/api_client.dart:37)
error - Undefined name 'AuthTokens'                            (services/api_client.dart:42)
```

Causa raiz, lida diretamente no código (`lib/services/api_client.dart`):
1. O import `import 'core/api_config.dart';` está errado — o arquivo real está em `lib/core/api_config.dart`, mas o import é relativo a `lib/services/`, então deveria ser `'../core/api_config.dart'`.
2. Faltam os imports de `SessionService` (`../services/session_service.dart` — que é o próprio arquivo, então nem precisaria de import, mas a classe é referenciada como tipo de parâmetro do construtor sem estar definida no arquivo) e `AuthTokens` (`../models/auth_tokens.dart`).
3. A classe `ApiClient` nunca declara um getter público `Dio get dio => _dio;`, mas três repositórios (`auth_repository.dart`, `dashboard_repository.dart`, `goalkeeper_repository.dart`) chamam `_apiClient.dio.get/post(...)`.
4. Mesmo corrigindo o getter, **o `Dio()` principal nunca recebe `BaseOptions(baseUrl: ApiConfig.baseUrl)`** — só a instância descartável dentro de `_refreshToken()` tem baseUrl configurada. Ou seja, mesmo consertando os erros de compilação, as chamadas normais (login, dashboard, goalkeepers) sairiam sem base URL.

Pelo `git log`, o commit mais recente do repositório (`6268ba9 fix: Corrigir importações incorretas de api_config e session_service`, gerado via Aider/`qwen3:30b`) é justamente quem **introduziu** essa quebra (removeu 42 linhas, adicionou 14) tentando corrigir imports — e não terminou o trabalho.

### 4.5 Modelos de dados (Dart)

`AuthUser`, `AuthTokens`, `Goalkeeper`, `DashboardData` — todos simples, com `fromJson`/`toJson` manuais (sem `json_serializable`/codegen). Coerentes com os schemas do backend.

### 4.6 Componentes reutilizáveis

Existem alguns widgets privados reaproveitados dentro de `main.dart` (`_Bloco`, `_CardIndicador`, `_TelaSecao`, `_MetricaSecao`, `_Etiqueta`), mas por serem classes privadas de um único arquivo, não são reutilizáveis fora dele — o "reuso" é só dentro do mesmo arquivo de 1800 linhas.

### 4.7 Testes

Um único teste de widget (`test/widget_test.dart`), testando apenas se a tela de login renderiza os textos esperados. **Não roda hoje**, pois depende de `AuthRepository`/`ApiClient`, que não compilam (Etapa 4.4).

### 4.8 O que falta (frontend)

- Corrigir a integração HTTP (bloqueante — nada funciona sem isso).
- Telas de Clubes, Goleiros, Vídeos, Análises, Sessões, Relatórios, Telegram, Usuários e Configurações: toda a camada de dados/CRUD real.
- Upload de vídeo pela UI (o botão "Enviar Vídeo" existe visualmente, mas `onPressed: () {}`).
- Tratamento de papéis/permissões na UI (não existe, pois também não existe no backend).
- Internacionalização formal (hoje pt-BR hardcoded em cada string).

---

## Etapa 5 — Inventário da IA

**Não implementado.** A pasta `ai_worker/` existe mas está **completamente vazia** (nenhum arquivo, nem mesmo um `.gitkeep`).

Não há, em nenhum lugar do repositório:
- Código de OpenCV, YOLO, MediaPipe, DeepSORT/ByteTrack ou qualquer biblioteca de visão computacional.
- Nenhum pipeline de treinamento ou inferência.
- Nenhum consumidor de fila/worker que leia os `ProcessingJob` criados pelo backend.
- Nenhuma integração real entre o backend e um "worker" (o campo `worker_id` existe na tabela `processing_jobs`, mas nunca é preenchido por código nenhum).

Tudo o que existe sobre IA é **documentação de intenção**:
- `docs_ai_worker_spec.md`: especifica pipeline (pré-processamento → detecção → tracking → segmentação de eventos → classificação → geração de artefatos → upload de resultados), autenticação do worker via `X-Worker-Api-Key` + HMAC, e observações sobre GPUs AMD (ROCm) com fallback ONNX/CPU.
- `docs_architecture_overview.md`: menciona RAG (Milvus/Weaviate/pgvector), assistente de IA, WebSocket para validação — nada disso está no código.

**Conclusão da Etapa 5:** o "AI" do "Goalkeeper AI" hoje é 0% implementado. O sistema atual é, na prática, um CRUD de cadastro + upload de arquivo para object storage.

---

## Etapa 6 — Docker

### Como iniciar o ambiente (hoje)

```bash
cd backend_fastapi
docker compose up --build
```

Isso sobe **apenas dois containers**:

| Container | Imagem | Porta host→container | Observações |
|---|---|---|---|
| `goalkeeper_ai_db` | `postgres:16-alpine` | `5433:5432` | Usuário/senha fixos no compose (`goalkeeper_user`/`goalkeeper_pass`), healthcheck via `pg_isready` |
| `goalkeeper_ai_backend` | build local (`Dockerfile`) | `8001:8001` | `uvicorn --reload`, depende de `postgres` saudável, monta todo o repo como volume (`.:/app`) |

- **Rede:** rede padrão criada implicitamente pelo Compose (não há rede nomeada customizada).
- **Volumes:** `postgres_data` (dados do Postgres) e um bind-mount `.:/app` no backend (útil para dev, mas não deveria ser usado em produção pois expõe o `.env` inteiro dentro do container e ignora a imagem construída).
- **Variáveis de ambiente:** definidas diretamente no `docker-compose.yml` (incluindo `JWT_SECRET_KEY: dev-secret-key-change-in-production` hardcoded) — não usa `env_file`, então o `.env` real (com as credenciais R2) **não é nem carregado automaticamente pelo compose**; ele só é lido localmente pelo Pydantic Settings quando rodado fora do Docker.
- **Frontend:** tem `Dockerfile` próprio, mas **não está incluído em nenhum `docker-compose.yml`** — precisa ser buildado/rodado manualmente.
- **AI Worker:** comentário reservando a porta 8002, sem nenhum serviço real.

---

## Etapa 7 — Dívida Técnica

Classificação: 🔴 Crítico | 🟠 Alto | 🟡 Médio | 🟢 Baixo

### 7.1 🔴 Segredos reais versionados no Git

- O arquivo `` 1. `backend_fastapi/.env` `` (nome literal corrompido, com prefixo numérico e crase — ver 7.4) está **rastreado no commit `HEAD`** e contém:
  - `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` com valores que aparentam ser credenciais reais da Cloudflare R2.
  - O mesmo conjunto de valores está replicado em `backend_fastapi/.env.example` (o arquivo "de exemplo" contém segredos reais, não placeholders).
- `core/security.py::hash_password()` tem `print()`s de debug que **imprimem a senha em texto puro** no log/stdout a cada registro de usuário (linhas 22-27) — ativo em produção.
- **Ação recomendada imediata:** revogar/rotacionar as credenciais R2 expostas, remover o arquivo do histórico do Git (`git filter-repo` ou BFG), adicionar `.env` ao `.gitignore` (hoje o `.gitignore` da raiz só ignora `.aider*`), e remover os `print()` de senha.

### 7.2 🔴 Frontend não compila

Ver Etapa 4.4. `flutter analyze` falha com 12 erros. O app Flutter, no estado atual do repositório, **não builda** em nenhuma plataforma. Qualquer avaliação de "o frontend está pronto" deve ser descartada até isso ser corrigido.

### 7.3 🟠 Ausência quase total de autenticação/autorização nas rotas de negócio

De ~30 endpoints, só `/auth/me` exige token. Qualquer pessoa com acesso à URL da API pode ler/criar/editar/apagar clubes, goleiros, sessões, vídeos e jobs, e ainda listar todos os usuários (incluindo e-mails) do sistema. Os endpoints de diagnóstico R2 (`/r2/health`, `/r2/test-upload`) também estão abertos e realizam operações de escrita real no bucket.

### 7.4 🟠 Poluição e ruído no histórico/árvore do Git

- 8 arquivos com nomes corrompidos (formato `` N. `caminho/original` ``) aparecem como "deletados" no `git status`, mas alguns (como o `.env`) ainda estão **tracked no HEAD**. Isso indica que uma automação (Aider) colou uma lista numerada de nomes de arquivo como se fosse um único nome de arquivo, criando cópias fantasmas dos arquivos reais.
- A raiz do repositório tem **~30 arquivos `.md`/`.txt`** de relatórios de sprints/auditorias passadas (`SPRINT_2A_*`, `SPRINT_2B_*`, `AUTH_FIX_*`, `PORT_AUDIT_*`, `RELATORIO_FINAL.txt`, etc.), competindo em visibilidade com a documentação atual e dificultando saber "qual é a fonte da verdade".
- `IA_GK.zip` e a pasta `.serena/` estão soltos na raiz, não deveriam estar versionados/no working tree do repositório de código.
- Resíduos do Aider (`.aider.chat.history.md`, `.aider.input.history`, `.aider.tags.cache.v4/`) presentes no diretório (parcialmente cobertos pelo `.gitignore` desde o commit `837561b`).

### 7.5 🟡 Refresh token não é rotacionado

`AuthService.refresh_access_token` gera um novo `access_token` mas devolve o **mesmo** `refresh_token` recebido (`auth_service.py:88`) — o refresh token nunca expira na prática enquanto for reaproveitado, e não há mecanismo de revogação/blacklist.

### 7.6 🟡 `Base.metadata.create_all` concorrendo com Alembic

`main.py` roda `create_all` no startup **além** das migrations Alembic existentes — risco de divergência entre schema "criado automaticamente" e schema "migrado", especialmente perigoso se alguém rodar a app antes de aplicar uma migration nova.

### 7.7 🟡 CORS mal configurado

`allow_origins=["*"]` combinado com `allow_credentials=True` é uma configuração inconsistente com a especificação CORS e um anti-padrão de segurança.

### 7.8 🟡 Tratamento de exceção frágil em `VideoUploadService.upload_video`

Se uma exceção ocorrer antes da linha que define `temp_path` (ex.: falha ao criar o diretório), o bloco `except` no final do método referencia `temp_path` que pode não estar definida, gerando um `UnboundLocalError` mascarando o erro original.

### 7.9 🟢 Código morto / inacabado no frontend

- `GoalkeeperProvider` implementado mas nunca registrado/usado.
- `GET /goalkeepers` sem `club_id` retorna `[]` fixo em vez de listar todos os goleiros (contradiz o padrão usado nos outros endpoints de listagem).
- `passlib[bcrypt]==1.7.4` duplicado em `requirements.txt`.
- Uso de `print()` para log de erro em `GoalkeeperProvider` (Dart) em vez de um logger adequado.

### 7.10 Priorização consolidada

| # | Item | Prioridade |
|---|---|---|
| 1 | Rotacionar credenciais R2 e remover segredos do histórico do Git | 🔴 Crítico |
| 2 | Corrigir `api_client.dart` (imports + getter `dio` + baseUrl) para o frontend voltar a compilar | 🔴 Crítico |
| 3 | Remover `print()` de senha em texto puro | 🔴 Crítico |
| 4 | Adicionar autenticação/autorização em todos os endpoints de negócio | 🟠 Alto |
| 5 | Limpar arquivos de nomes corrompidos do Git | 🟠 Alto |
| 6 | Rotacionar refresh tokens / implementar revogação | 🟡 Médio |
| 7 | Remover `create_all` automático, depender só do Alembic | 🟡 Médio |
| 8 | Corrigir política de CORS | 🟡 Médio |
| 9 | Organizar/arquivar relatórios `.md` soltos na raiz | 🟢 Baixo |
| 10 | Remover código morto (`GoalkeeperProvider`, duplicata no requirements.txt) | 🟢 Baixo |

---

## Etapa 8 — Estado Atual

### ✅ Pronto (funcional em nível de código, não testado em produção)
- CRUD de Clubes, Treinadores, Goleiros, Sessões de Treino (backend).
- Registro/login/refresh/me com JWT.
- Upload de vídeo real para Cloudflare R2, com criação de registro `Video` + `ProcessingJob`.
- Migrations Alembic consistentes com os models atuais.
- Tela de login e painel (dashboard) do Flutter, com integração real à API (quando o app compilar).

### 🟡 Parcialmente pronto
- Frontend Flutter: 9 das 11 telas são apenas protótipos visuais com dados fictícios fixos, sem integração real.
- Segurança: existe autenticação, mas não há autorização/RBAC nem proteção da maior parte das rotas.
- Ambiente Docker: sobe backend + banco, mas não sobe frontend nem worker.

### ❌ Não implementado
- AI Worker (detecção, tracking, classificação de eventos) — pasta vazia.
- Geração de relatórios (PDF).
- RAG / assistente de IA / busca semântica.
- Integração com Telegram.
- Testes automatizados (backend: só `__init__.py` vazio; frontend: 1 teste, que não roda hoje).
- CI/CD (sem `.github/workflows` ou equivalente).
- Multi-tenancy / isolamento de dados por clube.
- Infraestrutura como código (`infra/` vazio, apesar de a documentação mencionar Terraform/Kubernetes).

---

## Etapa 9 — Roadmap (Sprints)

> Este roadmap prioriza estabilizar o que já existe antes de expandir escopo, dado o estado encontrado nas Etapas 7 e 8.

### Sprint 0 — Estabilização e Segurança (urgente, antes de qualquer nova feature)
- **Objetivo:** eliminar os riscos críticos encontrados e destravar o build do frontend.
- **Arquivos envolvidos:** `backend_fastapi/.env*`, `.gitignore`, `app/core/security.py`, `frontend_flutter/lib/services/api_client.dart`, histórico do Git (arquivos de nome corrompido).
- **Impacto:** sem isso, há exposição ativa de credenciais e o app mobile/web não builda.
- **Riscos:** reescrita de histórico do Git (para remover segredos) afeta todos os clones existentes — precisa de coordenação com quem mais tem o repositório.
- **Estimativa:** 2-3 dias.

### Sprint 1 — Segurança de API (autenticação/autorização real)
- **Objetivo:** proteger todos os endpoints de negócio com JWT + checagem de papel/posse (ex.: um coach só vê goleiros do seu clube).
- **Arquivos envolvidos:** todos os routers em `app/api/v1/`, criação de dependências de autorização reutilizáveis (hoje `get_current_user` está isolado em `auth.py`, deveria mover para `core/`).
- **Impacto:** alto — muda o contrato de todas as chamadas do frontend (precisa enviar `Authorization` em tudo, não só em `/auth/me`).
- **Riscos:** quebra temporária de integração frontend↔backend se não for feito em conjunto com o Sprint 2.
- **Estimativa:** 1-1.5 semanas.

### Sprint 2 — Frontend: conectar as telas reais à API
- **Objetivo:** substituir os dados fictícios de Clubes, Goleiros, Vídeos e Sessões de Treino por chamadas reais (reaproveitando o padrão já usado em `DashboardRepository`), incluindo o fluxo de upload de vídeo pela UI.
- **Arquivos envolvidos:** `lib/main.dart` (deveria também ser quebrado em `screens/` separadas), novos repositories (`ClubRepository`, `TrainingSessionRepository`, `VideoRepository`).
- **Impacto:** entrega valor real de produto pela primeira vez (hoje o app é majoritariamente uma casca visual).
- **Riscos:** depende do Sprint 1 estar concluído (headers de auth) para não recomeçar o trabalho de integração duas vezes.
- **Estimativa:** 2-3 semanas.

### Sprint 3 — Fundações do AI Worker (mínimo viável)
- **Objetivo:** criar o serviço `ai_worker/` do zero: consumir `ProcessingJob`s pendentes, baixar vídeo do R2, rodar um pipeline mínimo de detecção (ex.: um único modelo YOLO pré-treinado, sem fine-tuning ainda), e postar eventos de volta via API (`docs_ai_worker_spec.md` já define o contrato desejado).
- **Arquivos envolvidos:** novo diretório `ai_worker/`, novos endpoints `app/api/v1/workers.py` no backend (autenticação via API key de worker), `docker-compose.yml` (novo serviço na porta 8002 já reservada).
- **Impacto:** primeira entrega de valor de "IA" real do produto.
- **Riscos:** maior risco técnico do roadmap — depende de infraestrutura de GPU e de decisões de stack (ROCm vs. ONNX/CPU) ainda não validadas.
- **Estimativa:** 3-4 semanas (spike técnico recomendado antes de comprometer prazo).

### Sprint 4 — Qualidade: testes automatizados e CI
- **Objetivo:** suíte de testes de integração para o backend (pytest + banco de teste), testes de widget corrigidos no frontend, pipeline de CI (lint + testes) em GitHub Actions.
- **Arquivos envolvidos:** `backend_fastapi/tests/`, `frontend_flutter/test/`, novo `.github/workflows/`.
- **Impacto:** reduz risco de regressão à medida que Sprints 1-3 avançam.
- **Riscos:** baixo, mas exige disciplina contínua para não virar dívida de novo.
- **Estimativa:** 1-2 semanas (podendo rodar em paralelo com o Sprint 3).

### Sprint 5 — Limpeza de repositório
- **Objetivo:** arquivar/mover os ~30 relatórios `.md` históricos da raiz para uma pasta `docs/archive/`, remover `IA_GK.zip` e `.serena/` do controle de versão, consolidar a documentação viva (`docs_*`) em um único índice.
- **Arquivos envolvidos:** raiz do repositório, `.gitignore`.
- **Impacto:** organizacional, facilita onboarding de novos colaboradores.
- **Riscos:** nenhum funcional.
- **Estimativa:** 2-3 dias.

---

*Fim do relatório. Nenhuma funcionalidade foi presumida além do que está presente no código; onde a implementação não existe, foi explicitamente marcado como "Não implementado".*
