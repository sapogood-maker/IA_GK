# SPRINT_REPORT.md — Sprint 1 (Autenticação/autorização real nos endpoints)

> Referência: `PROJECT_ANALYSIS.md`, seção 7.10, item 4 ("Adicionar autenticação/autorização em todos os endpoints de negócio").

## Objetivo

Exigir um JWT válido (`Authorization: Bearer <token>`) em todos os endpoints de negócio do backend, que hoje estão publicamente acessíveis (achado 3.1 e 7.3 do `PROJECT_ANALYSIS.md`), sem alterar assinaturas de endpoints, nomes públicos ou o comportamento de `/auth/register`, `/auth/login` e `/auth/refresh` (que precisam continuar públicos).

**Escopo decidido para esta sprint (comunicado antes de iniciar):** apenas **autenticação** (exigir um token válido). Autorização granular por papel/posse (ex.: um `coach` só ver goleiros do próprio clube) ficou **fora** — depende de regras de negócio ainda não definidas e mudaria queries em vários repositórios, o que é um escopo maior e mais arriscado do que o gap crítico atual (endpoints totalmente abertos). Registrado como pendência.

## Arquivos modificados

| Arquivo | Alteração |
|---|---|
| `backend_fastapi/app/core/security.py` | Recebeu a dependência `get_current_user` (movida de `auth.py`), com os imports necessários (`Depends`, `Header`, `HTTPException`, `status`, `AsyncSession`, `get_db`, `UserRepository`) |
| `backend_fastapi/app/api/v1/auth.py` | Removida a definição local de `get_current_user`; agora importa de `app.core.security`; removidos os imports que só eram usados por ela (`Header`, `UUID`, `UserRepository`) |
| `backend_fastapi/app/api/v1/users.py` | `router = APIRouter(..., dependencies=[Depends(get_current_user)])` |
| `backend_fastapi/app/api/v1/clubs.py` | idem |
| `backend_fastapi/app/api/v1/coaches.py` | idem |
| `backend_fastapi/app/api/v1/goalkeepers.py` | idem |
| `backend_fastapi/app/api/v1/training_sessions.py` | idem |
| `backend_fastapi/app/api/v1/videos.py` | idem |
| `backend_fastapi/app/api/v1/processing_jobs.py` | idem |
| `backend_fastapi/app/api/v1/r2.py` | idem (inclui os endpoints de diagnóstico `/r2/health` e `/r2/test-upload`, que antes permitiam qualquer um acionar leitura/escrita real no bucket) |

`backend_fastapi/app/api/v1/auth.py` **não** recebeu `dependencies` no nível do router — `/register`, `/login` e `/refresh` continuam públicos por definição (é como o cliente obtém o token); `/me` manteve seu próprio `Depends(get_current_user)` explícito, sem alteração de comportamento.

## Decisões arquiteturais

- **`get_current_user` foi movido de `app/api/v1/auth.py` para `app/core/security.py`.** Antes, era uma função isolada usada só por `/me`; para reutilizá-la em 8 routers diferentes sem que eles dependessem de um módulo-irmão (`api.v1.auth`), o lugar natural é `core/security.py`, que já concentra a lógica de JWT (`decode_token`, `create_token`). Verifiquei a cadeia de imports (`core/security.py` → `db/base.py` → `core/config.py`; `core/security.py` → `repositories/repositories.py` → `models/models.py` → `db/base.py`) para confirmar que não há import circular.
- **Proteção aplicada via `dependencies=[Depends(get_current_user)]` no `APIRouter`**, não como parâmetro de cada função de endpoint. Isso protege todas as rotas do arquivo com uma única linha, sem tocar em nenhuma assinatura de função existente — a menor mudança possível para resolver o problema, e o mesmo padrão repetido nos 8 arquivos (fácil de auditar).
- **Nenhuma mudança no frontend foi necessária.** O `ApiClient` (corrigido na Sprint 0) já injeta `Authorization: Bearer <token>` em toda requisição via interceptor, então o fluxo login → painel continua funcionando sem alteração.

## Testes/verificações executados

| Verificação | Resultado |
|---|---|
| `python -m py_compile` em todos os módulos alterados e no restante de `app/` | **Sem erros de sintaxe** |
| Verificação manual da cadeia de imports (busca por ciclos) | **Sem import circular** entre `core/security.py`, `db/base.py`, `repositories/repositories.py`, `models/models.py` |
| Busca por referências antigas a `get_current_user` importado de `api.v1.auth` | **Nenhuma** — só era usado dentro do próprio `auth.py` |
| Execução real do servidor (`uvicorn`) / testes de integração hitando os endpoints com e sem token | **Não executado** — tentei criar um venv isolado e instalar `requirements.txt` para rodar a app de verdade, mas a instalação falhou: `pydantic-core==2.5.0` (dependência do Pydantic 2.5) precisa compilar via Rust/maturin nesta máquina rodando **Python 3.14**, e o linker do MSVC falhou. O `Dockerfile` do projeto fixa `python:3.11-slim`; o ambiente local não tem 3.11 disponível. Isso é uma limitação pré-existente do ambiente, não relacionada a esta mudança — fica registrado como pendência de verificação (ideal rodar via `docker compose up` para confirmar em runtime) |
| Testes automatizados de backend | Não há suíte (`tests/` só tem `__init__.py`, achado já registrado no `PROJECT_ANALYSIS.md`) |
| Frontend (`flutter analyze` / `flutter test`) | Não re-executado nesta sprint — nenhum arquivo Dart foi tocado |

## Pendências

1. **Verificação em runtime real** (subir `docker compose up` e testar com `curl`/Postman que rotas de negócio agora retornam `401` sem token e `200` com token válido) — recomendo antes de considerar esta sprint "fechada" em produção, já que não consegui rodar a aplicação localmente pela limitação de ambiente (Python 3.14 vs. dependências pinadas para 3.11).
2. **Autorização granular por papel/posse** (ex.: coach só vê goleiros do próprio clube; endpoints de escrita restritos a papéis específicos) — decisão de escopo explicada acima, fica para uma sprint futura, após definição das regras de negócio por papel.
3. Endpoints de refresh token continuam sem rotação (achado 7.5 do `PROJECT_ANALYSIS.md`) — não fazia parte do escopo desta sprint.

## Próximos passos sugeridos

1. Validar esta sprint subindo o ambiente via Docker (`docker compose up` em `backend_fastapi/`) e confirmando manualmente os códigos de resposta 401/200.
2. Seguir para a **Sprint 2 — Conectar as telas do Flutter à API** (Clubes, Goleiros, Vídeos, Sessões de Treino, upload de vídeo pela UI), já que o backend agora exige autenticação e o `ApiClient` já está corrigido para propagá-la.

Aguardando sua aprovação para a próxima sprint.
