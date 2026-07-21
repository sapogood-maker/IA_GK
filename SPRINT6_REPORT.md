# SPRINT6_REPORT.md — Consolidação da Plataforma

> Escopo: auditoria completa + correção de pendências arquiteturais reais. Nenhuma linha relacionada ao AI Worker foi criada (sem Redis, fila, YOLO, OpenCV, tracking, modelos de IA, Docker de Worker ou endpoints específicos do Worker). Análise prévia de `AI_WORKER_ARCHITECTURE.md`, `DOMAIN_ARCHITECTURE.md` e `SPRINT5_REPORT.md` confirmou compatibilidade de todas as mudanças antes de qualquer alteração de arquivo.

## 1. Revisão geral — problemas encontrados e corrigidos

Rodei uma auditoria objetiva com `ruff` (linter Python; não havia nenhum configurado no projeto) para encontrar imports/variáveis mortos de forma confiável, em vez de inspeção manual arquivo por arquivo.

| # | Achado | Onde | Correção |
|---|---|---|---|
| 1 | `io`, `tempfile` importados e nunca usados | `app/core/r2.py` | Removidos |
| 2 | Variáveis `bucket_info`/`response` atribuídas e nunca usadas | `app/core/r2.py`, `app/api/v1/r2.py` | Removida a atribuição, mantida a chamada (que já valida como efeito colateral) |
| 3 | `except FileNotFoundError as e` com `e` não usado | `app/core/r2.py` | Removido o bind |
| 4 | `ProcessingJobStatusResponse`, `ProcessingJobRepository` importados e nunca usados | `app/api/v1/videos.py` | Removidos |
| 5 | `get_db` importado e nunca usado | `app/core/authorization.py` | Removido |
| 6 | `R2ValidationError` importado e nunca usado (sobrou do `create_all`/validação antiga) | `app/main.py` | Removido |
| 7 | `CoachRepository`, `GoalkeeperRepository` importados e nunca usados | `app/services/auth_service.py` | Removidos |
| 8 | `ProcessingJobRepository.get_by_video_id` sem `ORDER BY` — `VideoUploadService.get_video_status` assume que `jobs[0]` é o job mais recente, mas o Postgres não garante ordem sem `ORDER BY` explícito | `app/repositories/repositories.py` | Adicionado `ORDER BY created_at DESC` |
| 9 | Índice duplicado em `users.email` (`Column(unique=True, index=True)` cria dois índices sobre a mesma coluna) | `app/models/models.py` | Removido `index=True` (o `unique=True` já cria o índice); migration `005` remove o índice redundante do banco |
| 10 | **Endpoints "legacy"** (`POST /videos` cria registro sem passar pelo R2; CRUD manual de `processing-jobs`) não são usados pelo Flutter hoje | `app/api/v1/videos.py`, `processing_jobs.py` | **Não removidos** — o CRUD de `processing-jobs` é exatamente a superfície que o futuro AI Worker vai usar (`AI_WORKER_ARCHITECTURE.md`); registrado como achado, não como correção, para não contradizer a preparação para o Worker |

Nenhuma refatoração cosmética foi feita — cada item acima ou corrige um bug real (achados 8, 9) ou remove código morto confirmado por ferramenta (achados 1-7).

## 2. Alembic — fluxo único e oficial (resolvido definitivamente)

**Antes:** `app/main.py` rodava `Base.metadata.create_all` no startup, coexistindo com as migrations do Alembic. Isso já tinha causado um problema real e documentado na Sprint 5 (uma tabela existente não ganhava uma coluna nova, porque `create_all` só cria tabelas que não existem).

**Depois:**
- `create_all` foi **removido** de `app/main.py`. A aplicação não cria/altera nada no banco em runtime.
- `docker-compose.yml`: o comando do container agora é `sh -c "alembic upgrade head && uvicorn ..."` — migrations rodam automaticamente antes do servidor subir.
- `LOCAL_SETUP.md` atualizado com o passo `alembic upgrade head` (antes ausente, pois dependia do `create_all` implícito).

**Validado explicitamente nos dois cenários pedidos:**
- **Ambiente novo**: `docker compose up --build` do zero aplica as 5 migrations (`001→005`) automaticamente antes do servidor responder.
- **Ambiente já existente**: simulei um ambiente "parado na Sprint 5" (`alembic downgrade 004` contra o volume já rodando) e reiniciei o container — aplicou **somente** a migration `005` pendente, sem tocar no resto.

## 3. Testes automatizados (não existia nenhum)

Criada a suíte em `backend_fastapi/tests/` (`pytest` + `pytest-asyncio` + `httpx`, adicionados ao `requirements.txt`; banco de teste separado, nunca o de desenvolvimento/produção). **30 testes, todos passando**, cobrindo exatamente as prioridades pedidas:

| Arquivo | Cobertura |
|---|---|
| `test_auth.py` | Bootstrap do 1º admin, bloqueio de autopromoção, exigência de clube válido, login (sucesso/falha), refresh (rotação), proteção de `/me` |
| `test_authorization.py` | Isolamento entre clubes (clubes, goleiros, sessões — incluindo o caminho transitivo via *join*), bypass de `SYSTEM_ADMIN`, restrição de `/users` e `/r2/health` a admin |
| `test_video_upload.py` | Validação de arquivo (unitário, sem banco/rede), autenticação e autorização do upload (sem precisar de credenciais reais do R2, pois o *check* de posse roda antes de qualquer chamada ao R2) |

**Dois bugs reais e sérios foram descobertos só porque os testes passaram a existir** (nenhuma sprint anterior, incluindo testes manuais via `curl`, tinha exercitado `/auth/refresh` de ponta a ponta):

1. **`/auth/refresh` sempre retornava 401`, desde o início do projeto.** `decode_token` exigia um claim `email` no payload, mas o refresh token nunca carregou esse campo (só `user_id`). Corrigido tornando `email`/`role` opcionais em `TokenData` — só `user_id` é obrigatório em qualquer token.
2. **A "rotação" do refresh token (Sprint 6) podia devolver um token idêntico ao anterior** se emitido no mesmo segundo — o payload só tinha `user_id` + `exp` (truncado ao segundo), sem nenhum claim de unicidade. Corrigido adicionando um `jti` (JWT ID) aleatório a cada emissão. Aproveitei para consolidar as 3 chamadas duplicadas de criação de refresh token num único helper (`_create_refresh_token`).

## 4. Frontend — revisão (sem mudanças de código)

Todas as 10 telas foram revisadas. **7 já são reais** (Painel, Clubes, Goleiros, Vídeos, Sessões de Treino, Usuários, Configurações — as duas últimas desde a Sprint 5). **3 continuam mock, e suas dependências foram confirmadas e documentadas, não removidas:**

| Tela | Por que continua mock |
|---|---|
| **Análises** | Depende inteiramente do AI Worker — não há como ser real sem as tabelas `Event`/`Analysis` (já existem, Sprint 5) serem populadas por um processamento de vídeo que ainda não existe |
| **Relatórios** | Depende de `Report` (já existe, Sprint 5) ser gerado a partir de análises reais — mesmo bloqueio |
| **Telegram** | Depende de uma integração de notificação ainda não construída (decisão de produto sobre gatilhos de notificação, fora do escopo de "consolidação") |

`flutter analyze`/`flutter test`/`flutter build web` seguem limpos — nenhuma mudança foi necessária no frontend nesta sprint.

## 5. Modelo de dados — revisão

- Índice duplicado em `users.email` corrigido (seção 1, achado 9).
- Query sem `ORDER BY` corrigida (seção 1, achado 8).
- **Cascades revisados** (`ondelete` de cada FK) — todos consistentes com a semântica esperada (ex.: apagar um clube não apaga o usuário vinculado, `SET NULL`; apagar uma análise apaga seus eventos/métricas/artefatos, `CASCADE`). Nenhuma mudança necessária.
- **Nullable/unique**: revisados, nenhuma inconsistência encontrada além do índice duplicado já corrigido.
- Nenhuma mudança "por preferência pessoal" foi feita — só os dois achados com ganho técnico real e demonstrável.

## 6. Status oficiais — confirmação

**Uma única definição** (`ProcessingJobStatus`, em `app/models/models.py`), reutilizada por `ProcessingJob.status` e `Analysis.status` desde a Sprint 5. O Frontend usa exatamente os mesmos 11 valores (`_rotuloStatusVideo` em `main.dart`, também da Sprint 5). Nenhuma duplicação encontrada — nada a corrigir aqui nesta sprint.

## 7. Auditoria da API

- Todos os 34 endpoints inspecionados via `openapi.json` da aplicação rodando de verdade.
- **Achado corrigido**: nenhum endpoint protegido documentava `401`/`403`/`404` no Swagger — FastAPI só lista no OpenAPI o que é declarado explicitamente, não exceções levantadas em runtime. Adicionado `responses=COMMON_ERROR_RESPONSES` (novo, em `app/core/authorization.py`) a todos os 8 routers protegidos, documentando os 3 códigos de forma padronizada e centralizada (não duplicada endpoint por endpoint).
- Autenticação/autorização/validação/mensagens de erro/códigos HTTP: já consistentes desde a Sprint 5, confirmados novamente aqui via os testes automatizados novos.

## 8. Segurança — revisão

| Item | Situação |
|---|---|
| JWT / `HTTPBearer` | Funcionando corretamente (Swagger Authorize confirmado em sprint anterior) |
| Refresh Token | **Dois bugs reais corrigidos** (seção 3) — antes, o fluxo inteiro nunca funcionava |
| Upload | Validação de extensão/MIME/tamanho já testada; autorização confirmada antes de qualquer chamada ao R2 |
| Permissões (RBAC) | Testada exaustivamente (30 testes) |
| Acesso ao R2 | Credenciais mestras seguem exclusivas do backend; `/r2/health` e `/r2/test-upload` restritos a `SYSTEM_ADMIN` desde a Sprint 5 |
| Variáveis de ambiente | Revisadas nas sprints de estabilização anteriores; nada novo encontrado |
| **CORS (`allow_origins=["*"]` + `allow_credentials=True`)** | **Risco real, ainda não corrigido.** Já flagueado no `PROJECT_ANALYSIS.md` original. Não corrigi agora porque a correção certa (restringir a origens específicas) exige saber o(s) domínio(s) real(is) de produção/Coolify, que não tenho — corrigir com um palpite errado quebraria o acesso legítimo. Recomendo definir os domínios de produção e restringir isso na próxima sprint de infraestrutura |
| Revogação de refresh token | Segue sem blacklist server-side (JWT é stateless; blacklist exigiria armazenamento persistente — decisão consciente de não implementar, para não confundir com infraestrutura do Worker) |

## 9. Documentação atualizada

- `DOMAIN_ARCHITECTURE.md`: adendo "Sprint 6" explicando a resolução do `create_all`/Alembic, o índice corrigido, os bugs de refresh token e a nova suíte de testes.
- `LOCAL_SETUP.md`: passo de `alembic upgrade head` adicionado (antes dependia do `create_all` implícito, que não existe mais).
- Este relatório (`SPRINT6_REPORT.md`).

## 10. Testes/validações executados (todos passaram)

| Verificação | Resultado |
|---|---|
| `ruff check` (novo, auditoria) | 0 achados após as correções |
| `python -m py_compile` em todo o backend | Sem erros |
| `pytest` (novo — 30 testes) | **30 passaram** |
| `flutter analyze` | 0 erros, 0 avisos |
| `flutter test` | 1/1 passou |
| `flutter build web --release` | Build concluído |
| `docker compose up --build` — ambiente novo | Migrations `001→005` aplicadas automaticamente; containers `healthy` |
| `docker compose` — ambiente já existente (simulado) | Só a migration pendente (`005`) aplicada ao reiniciar |
| Bateria de smoke test real (health, bootstrap admin, `/me`, R2 real, refresh) | Tudo `200`, refresh funcionando pela primeira vez |

## 11. Pendências restantes (não corrigidas nesta sprint, com motivo)

1. **CORS permissivo** (`*` + credenciais) — precisa dos domínios de produção reais para corrigir com segurança.
2. **Endpoints "legacy"** (`POST /videos` manual, CRUD completo de `processing-jobs`) — mantidos deliberadamente; o CRUD de jobs é a interface que o AI Worker vai usar.
3. **Revogação server-side de refresh token** — precisaria de armazenamento persistente (fora do escopo desta sprint, que proíbe explicitamente infraestrutura nova).
4. **Fluxo de convite/aprovação de usuário** — hoje qualquer pessoa pode se autorregistrar como `treinador`/`clube`/`analista` de um clube existente sem aprovação; aceitável por ora, mas vale revisar quando o produto tiver clientes reais.
5. **CI/CD** — continua inexistente.
6. **Telas de Análises/Relatórios/Telegram** — bloqueadas até o AI Worker (as duas primeiras) ou uma decisão de produto sobre notificações (a terceira).

## 12. Avaliação honesta do projeto

| Área | % concluído | Justificativa |
|---|---|---|
| **Backend** | **~88%** | Auth, RBAC multi-tenant, CRUD completo, upload real ao R2, migrations/schema com fluxo único, testes automatizados dos fluxos críticos, 2 bugs de segurança reais corrigidos. Falta: CORS restrito, fluxo de convite de usuário, geração de relatório (depende do Worker) |
| **Frontend** | **~75%** | 7 de 10 telas reais e íntegras. As 3 restantes dependem de coisas que não existem ainda por definição (dados de IA, integração de notificação) — não é "trabalho faltando por descuido", é bloqueio genuíno de dependência |
| **Infraestrutura** | **~65%** | Docker/migrations sólidos e validados nos dois cenários (novo/existente). Falta: CI/CD, observabilidade (Prometheus/Grafana), e toda a infraestrutura do Worker (deliberadamente fora desta sprint) |
| **Plataforma SaaS (geral)** | **~85%** | O núcleo do produto (cadastro multiempresa, autenticação, autorização, upload de vídeo) está sólido, testado e coerente. O que falta é essencialmente "camada de IA" e polimento operacional (CI/CD, CORS, observabilidade) |
| **Preparação para o AI Worker** | **~55%** | O que está pronto: modelo de dados (`Analysis`/`Event`/`Metric`/`Artifact`/`Report`), vocabulário oficial de status, isolamento por tenant resolvido de forma transitiva (o Worker não precisa saber o que é "clube"), arquitetura formalmente definida e documentada. O que falta é toda a **interface voltada ao Worker** propriamente dita (ver lista abaixo) |

## 13. O que ainda falta antes de iniciar o desenvolvimento do AI Worker

1. **Autenticação de máquina** (API Key + escopo de *service account*, `AI_WORKER_ARCHITECTURE.md` seção 6) — hoje só existe autenticação de usuário humano (JWT).
2. **Endpoints de URL assinada** para o Worker baixar vídeos e subir artefatos ao R2 sem nunca ver a credencial mestra (seção 11 do mesmo documento) — não existem ainda.
3. **Fila de processamento** (Redis, seção 4) — deliberadamente fora desta sprint.
4. **Repositório separado do Worker** (seção 8) — ainda não criado.
5. **Decidir e implementar** como o backend vai publicar uma mensagem na fila no momento do upload (hoje o `ProcessingJob` é criado mas nada o consome).
6. Opcionalmente, corrigir o CORS antes de expor a API para uma máquina de IA fora da rede confiável do SaaS.

Com isso resolvido, a plataforma está pronta para a Sprint A do roadmap do `AI_WORKER_ARCHITECTURE.md` (fundação de mensageria).

## 14. Git

Commit único cobrindo `backend_fastapi/` (código + testes + migration + docs) e os dois documentos de arquitetura na raiz. Nenhum arquivo de `frontend_flutter/` foi alterado (revisão sem necessidade de mudança). Nenhum arquivo relacionado a `ai_worker/`, Redis, fila ou modelos de IA foi criado.
