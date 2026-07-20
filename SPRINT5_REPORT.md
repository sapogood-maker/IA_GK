# SPRINT5_REPORT.md — Multi-tenancy + Autorização + Modelo de Dados

> Objetivo desta sprint: fechar o domínio do sistema como um SaaS multiempresa completo, **sem implementar nenhuma linha relacionada ao AI Worker** (sem Redis, fila, modelos de IA, OpenCV, YOLO, tracking ou pipeline de processamento). Confirmado como compatível com `AI_WORKER_ARCHITECTURE.md` antes de qualquer alteração (ver seção "Impacto para o AI Worker" abaixo).

## Arquitetura implementada

### Autorização (RBAC + multi-tenancy)

- 4 papéis oficiais (`UserRole`): `SYSTEM_ADMIN`, `CLUBE`, `TREINADOR`, `ANALISTA`.
- `User.club_id` (nulo só para `SYSTEM_ADMIN`, reforçado por `CHECK CONSTRAINT` no banco) é a fronteira de isolamento de todo o sistema.
- Novo módulo `app/core/authorization.py`, separado de `app/core/security.py` (autenticação ≠ autorização): dependência `require_roles(...)`, helpers `is_admin`/`effective_club_scope`, e resolvedores de posse via *join* explícito para as entidades que não têm `club_id` direto (`TrainingSession`, `Video`, `ProcessingJob`).
- **Analista tem exatamente o mesmo isolamento que Clube/Treinador** (confirmado com você): nenhum papel além de `SYSTEM_ADMIN` vê dados de outro clube. Sem suporte a usuário-em-vários-clubes nesta sprint (documentado como extensão futura via tabela de associação, se necessário).
- Todos os 8 routers (`users`, `clubs`, `coaches`, `goalkeepers`, `training_sessions`, `videos`, `processing_jobs`, `r2`) passaram a filtrar por clube em listagens e a validar posse em create/get/update/delete — sem alterar formato de request/response (só o **conjunto de dados retornado** mudou, que é exatamente o objetivo da sprint).
- **Bootstrap do primeiro admin**: o primeiro usuário registrado no sistema vira `SYSTEM_ADMIN` automaticamente (única forma de um admin existir, já que não há fluxo de convite/promoção). A partir do segundo usuário, autopromoção a `SYSTEM_ADMIN` é bloqueada (400) e `club_id` passa a ser obrigatório e validado contra um clube existente.

### Modelo de dados de IA (tabelas vazias, sem endpoints ainda)

5 entidades (refinei as 8 sugeridas como exemplo, evitando redundância — detalhes e justificativa completa em `DOMAIN_ARCHITECTURE.md`):
`Analysis` (versionada), `Event`, `Metric`, `Artifact`, `Report`. Nenhuma tem `club_id` próprio — o isolamento é herdado transitivamente pela cadeia `Video → TrainingSession → Goalkeeper → Club`, compatível com `AI_WORKER_ARCHITECTURE.md` (o Worker nunca precisa saber o que é "clube").

### Versionamento

`Analysis.version` incrementado por vídeo, com `UniqueConstraint(video_id, version)`. Nenhuma análise é sobrescrita — cada novo processamento gera uma linha nova.

### Status oficiais

`ProcessingJobStatus` expandido para os 11 estados pedidos (`QUEUED`, `DOWNLOADING`, `PREPROCESSING`, `INFERENCE`, `POSTPROCESSING`, `GENERATING_REPORT`, `UPLOADING_RESULTS`, `COMPLETED`, `FAILED`, `CANCELLED` — mais `UPLOADED`, que mantive em `Video.upload_status`, pois representa o arquivo, não o pipeline de IA; justificativa completa em `DOMAIN_ARCHITECTURE.md`). Convertido de enum nativo do Postgres para `VARCHAR` (validado na aplicação) — enum nativo exige uma migration a cada novo valor futuro, `VARCHAR` é mais preparado para crescimento.

### Frontend

- **Usuários**: lista real (`GET /api/v1/users`, admin-only no backend), com nome/e-mail/papel/clube; trata 403 mostrando "acesso restrito" em vez de mock.
- **Perfis + Permissões + Configurações**: consolidadas numa única tela ("Configurações", já existente na navegação) em 3 seções — não criei 2 rotas novas no menu para "Perfis"/"Permissões" isoladamente, já que elas não existiam antes e o escopo combinado era enxuto:
  - **Meu perfil**: dados reais do usuário logado (nome, e-mail, papel, clube).
  - **Permissões por papel**: matriz somente-leitura descrevendo fielmente as regras que agora são realmente aplicadas no backend (não é mock — é documentação do comportamento real).
  - **Sistema**: status real do R2 (`GET /r2/health`), visível só para `SYSTEM_ADMIN` (aparece "restrito" para os demais, já que o endpoint agora também é admin-only).

## Arquivos alterados

### Backend

| Arquivo | Mudança |
|---|---|
| `app/models/models.py` | `UserRole` enum; `User.club_id` + FK + `CHECK CONSTRAINT`; `ProcessingJobStatus` expandido; `upload_status`/`status` de enum nativo para `VARCHAR`; novas entidades `Analysis`, `Event`, `Metric`, `Artifact`, `Report` |
| `app/schemas/schemas.py` | `UserBase.club_id`; `UserCreate.validate_role`; `ProcessingJobBase.status` default `QUEUED` |
| `app/core/authorization.py` **(novo)** | RBAC + isolamento por clube |
| `app/repositories/repositories.py` | `UserRepository.create(club_id=...)`, `.count()`, `.get_by_club_id()`; `get_by_club_id()` (via join) em `TrainingSessionRepository`, `VideoRepository`, `ProcessingJobRepository`; default `QUEUED` |
| `app/services/auth_service.py` | Bootstrap do primeiro admin; validação de papel/clube no registro |
| `app/services/video_upload_service.py` | `ProcessingJobStatus.QUEUED` no lugar de `PENDING` |
| `app/api/v1/auth.py` | `/me` passa a incluir `club_id` |
| `app/api/v1/users.py`, `clubs.py`, `coaches.py`, `goalkeepers.py`, `training_sessions.py`, `videos.py`, `processing_jobs.py`, `r2.py` | Autorização (papel + posse por clube) em todos os endpoints |
| `alembic/versions/004_add_authorization_and_ai_data_model.py` **(novo)** | Migration completa: `users.club_id`, conversão de enums para `VARCHAR`, criação das 5 tabelas novas |

### Frontend

| Arquivo | Mudança |
|---|---|
| `lib/models/auth_user.dart` | Campo `clubId` |
| `lib/repositories/user_repository.dart` **(novo)** | `GET /api/v1/users` |
| `lib/repositories/system_repository.dart` **(novo)** | `GET /api/v1/r2/health` |
| `lib/providers/user_provider.dart` **(novo)** | Estado da lista de usuários, trata 403 como "acesso restrito" |
| `lib/providers/system_provider.dart` **(novo)** | Estado do status do R2 |
| `lib/main.dart` | Registra os 2 novos providers; `UsuariosScreen` e `ConfiguracoesScreen` reescritas (reais); `_rotuloStatusVideo` atualizado para os 11 estados oficiais |
| `test/widget_test.dart` | Novos providers obrigatórios |

### Documentação

| Arquivo | Conteúdo |
|---|---|
| `DOMAIN_ARCHITECTURE.md` **(novo)** | Modelo de autorização, modelo de dados, relacionamento entre entidades, responsabilidade de cada módulo |
| `SPRINT5_REPORT.md` **(este arquivo)** | |

## Decisões tomadas (e onde divergi dos exemplos do pedido)

1. **5 entidades de IA, não 8** — descartei `Inference`/`FrameAnnotation`/`Prediction` como tabelas separadas. Predições brutas por frame (potencialmente milhares de linhas por vídeo) viram um artefato em lote no R2 via `Artifact`, não linhas individuais no Postgres — evita um problema de escala real quando "milhares de vídeos" vier a acontecer.
2. **Enum de status: `VARCHAR`, não enum nativo do Postgres** — mais fácil de estender no futuro (mesma lição já aprendida na sprint de estabilização, ao alterar `alembic.ini`/`DATABASE_URL`).
3. **Bug encontrado e corrigido durante o próprio desenvolvimento**: minha primeira versão do validador de `club_id` obrigatório rodava no schema Pydantic, **antes** da lógica de bootstrap do primeiro admin — travando o próprio bootstrap (ninguém conseguiria criar o primeiro usuário do sistema). Corrigido movendo essa validação para `AuthService.register`, onde já existe acesso ao banco para saber se é o primeiro usuário. Encontrado e corrigido durante a validação ao vivo (seção abaixo), não em produção.
4. **"Perfis" e "Permissões" consolidados em "Configurações"** — não existiam como itens de menu antes desta sprint; em vez de criar 2 rotas novas, consolidei como seções dentro da tela de Configurações já existente, mantendo o escopo enxuto combinado.
5. **R2 endpoints (`/r2/health`, `/r2/test-upload`) agora são admin-only** — são diagnósticos de infraestrutura do sistema, não dado de tenant; não fazia sentido nenhum papel de clube ter acesso a eles.

## Validações executadas

Toda a autorização foi validada **rodando a API de verdade** (não só análise estática), com `docker compose up --build` do zero e uma bateria completa de testes HTTP reais:

| Teste | Resultado |
|---|---|
| `python -m py_compile` em todo o backend | Sem erros |
| `flutter analyze` | 0 erros, 0 avisos |
| `flutter test` | 1/1 passou |
| `flutter build web --release` | Build concluído |
| `docker compose up --build` do zero | Ambos containers `healthy` |
| Migrações `001 → 004` | Aplicadas com sucesso; `users.club_id` + `CHECK CONSTRAINT` confirmados no schema |
| Bootstrap do 1º usuário → `system_admin` | Confirmado |
| Tentativa de autopromoção a `system_admin` (2º usuário em diante) | Bloqueada com `400` |
| Treinador cria goleiro no próprio clube | `201` |
| Treinador tenta criar goleiro em outro clube | `403` |
| Treinador lista goleiros | Vê só os do próprio clube |
| Treinador acessa goleiro de outro clube por id | `403` |
| Admin lista/acessa qualquer clube | Sem restrição |
| Treinador cria sessão de treino para goleiro de outro clube | `403` |
| Treinador lista sessões/vídeos/jobs (join triplo) | Escopado corretamente, sem erro de SQL |
| `GET /users` como treinador / admin | `403` / `200` (lista completa) |
| `GET /users/{id}` de outro usuário como treinador | `403` |
| `GET /r2/health`, `POST /r2/test-upload` como treinador / admin | `403` / `200` (confirmado real: leitura, escrita e exclusão no bucket configurado) |

## Achado durante a validação (não corrigido, fora do escopo desta sprint)

Ao testar `docker compose up --build` reaproveitando o volume Postgres de uma sprint anterior, confirmei na prática a tensão já registrada no `STABILIZATION_REPORT.md` entre `Base.metadata.create_all` (rodado no startup da app) e as migrations do Alembic: como o `create_all` só cria tabelas que **não existem**, ele criou as 5 tabelas novas de IA corretamente, mas **não adicionou `club_id` a uma tabela `users` já existente** de uma sprint anterior — precisei rodar `alembic upgrade head` manualmente (ou recriar o volume) para corrigir.

**Implicação prática**: um ambiente **já em produção/Coolify** rodando uma versão anterior deste projeto precisa executar `alembic upgrade head` manualmente ao fazer deploy desta sprint — o `create_all` sozinho não é suficiente para atualizar o schema de uma instalação existente. Instalações **novas** (banco vazio) continuam funcionando normalmente só com `create_all`. Recomendo resolver essa sobreposição definitivamente numa sprint futura de infraestrutura (rodar migrations automaticamente no entrypoint do container, e então remover o `create_all`).

## Impacto para o AI Worker

Nada foi implementado do Worker nesta sprint, mas a plataforma agora está pronta para recebê-lo sem precisar de mudanças estruturais:

- O Worker vai popular `Analysis`/`Event`/`Metric`/`Artifact` **via API do backend** (nunca escrita direta no banco), e o backend resolve o isolamento por clube sozinho — o Worker não precisa carregar nenhum conceito de tenant.
- O vocabulário de status (`ProcessingJobStatus`) já é o oficial que o Worker vai reportar via `PUT /api/v1/processing-jobs/{id}` (endpoint que já existe).
- A autenticação do Worker (API Key + service account, `AI_WORKER_ARCHITECTURE.md` seção 6) continua sendo um mecanismo separado do `UserRole` desta sprint — implementá-la é a próxima peça que falta antes do Worker poder chamar a API com segurança.

## Git

Somente arquivos de `backend_fastapi/` e `frontend_flutter/` foram alterados, mais os dois documentos na raiz (`DOMAIN_ARCHITECTURE.md`, `SPRINT5_REPORT.md`). Nenhum arquivo relacionado a `ai_worker/`, Redis, fila ou modelos de IA foi criado, conforme pedido.
