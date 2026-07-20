# AUTH_FIX_REPORT.md — Correção do esquema de autenticação (Swagger/OpenAPI)

> Referência: pedido explícito do usuário para trocar o header manual (`authorization: str = Header(...)`) pelo padrão oficial do FastAPI (`fastapi.security`), fazendo o botão "Authorize" do Swagger funcionar em todos os endpoints protegidos.
>
> Este relatório substitui uma versão anterior de `AUTH_FIX_REPORT.md` (datada de 2026-06-10, gerada por outra ferramenta) que documentava justamente a introdução do padrão `Header(...)` — o problema que esta correção resolve.

## Problema

`get_current_user`, em `backend_fastapi/app/core/security.py`, declarava o parâmetro `authorization: str = Header(...)` e fazia o parsing manual do header (`authorization.split(" ")[1]`). Isso funciona em tempo de execução, mas para o **OpenAPI/Swagger** é interpretado como um header genérico chamado `authorization` que precisa ser digitado manualmente em cada endpoint — não é reconhecido como um esquema de segurança Bearer/OAuth2, então:
- Não aparecia um cadeado consistente com um esquema de segurança real.
- O botão global "Authorize" do Swagger não injetava o token automaticamente nas chamadas.

## Onde a busca foi feita

Procurei por `Header(`, `OAuth2PasswordBearer`, `HTTPBearer` e uso manual de `Authorization`/`authorization` em todo `backend_fastapi/app/`. **Resultado: uma única ocorrência**, exatamente em `get_current_user` (`app/core/security.py`). Não havia nenhuma duplicidade de lógica de autenticação em outros arquivos — todos os 8 routers protegidos (`users`, `clubs`, `coaches`, `goalkeepers`, `training_sessions`, `videos`, `processing_jobs`, `r2`) e o endpoint `/auth/me` já dependem dessa única função (centralização feita em uma sprint anterior), então **corrigir esse único ponto corrige automaticamente todos os endpoints protegidos do sistema** — item 7 do pedido (centralizar em `get_current_user`) já estava satisfeito antes mesmo desta correção.

## Arquivo modificado

**`backend_fastapi/app/core/security.py`** — único arquivo alterado.

### O que mudou

- Removido `Header` do import de `fastapi`.
- Adicionado `from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer`.
- Criado `bearer_scheme = HTTPBearer(auto_error=False, description=...)` — instância do esquema de segurança oficial do FastAPI, registrada automaticamente no OpenAPI (`components.securitySchemes`).
- `get_current_user` agora recebe `credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)` em vez de `authorization: str = Header(...)`.
- A extração do token passa a ser `credentials.credentials` (já sem o prefixo `"Bearer "`, tratado pelo próprio FastAPI) em vez do `authorization.split(" ")[1]` manual.
- **Nenhuma regra de negócio foi alterada**: mesmos status codes (401 para header ausente/inválido, 401 para token inválido, 404 para usuário não encontrado) e mesmas mensagens de erro (`"Missing or invalid authorization header"`, `"Invalid token"`, `"User not found"`).

### Por que `HTTPBearer` e não `OAuth2PasswordBearer` (item 6 do pedido)

Verifiquei especificamente essa opção antes de decidir. `OAuth2PasswordBearer(tokenUrl=...)` faz o Swagger exibir, no botão "Authorize", um **formulário de usuário/senha** que envia um `POST` `application/x-www-form-urlencoded` com campos `username`/`password` diretamente para o `tokenUrl` configurado. O login real deste projeto (`POST /api/v1/auth/login`) é um endpoint **JSON** que espera `{"email": ..., "password": ...}` (schema `LoginRequest`) — não usa o campo `username` nem aceita form-urlencoded. Se eu apontasse um `OAuth2PasswordBearer` para essa rota, o formulário de login do Swagger **falharia ao tentar autenticar** (incompatibilidade de content-type e de nome de campo), o que violaria diretamente o requisito 8 ("validar que... funcionam utilizando apenas o botão Authorize") e o requisito 9 (não alterar contratos — mudar `/login` para aceitar `OAuth2PasswordRequestForm` quebraria o app Flutter já existente, violando também o requisito 5).

`HTTPBearer` é o construto oficial equivalente do `fastapi.security` para um esquema **Bearer puro** (sem assumir o fluxo de senha do OAuth2): registra o mesmo tipo de security scheme no OpenAPI, produz o mesmo cadeado por endpoint e o mesmo botão global "Authorize" — só que o usuário cola diretamente o `access_token` já obtido via `POST /api/v1/auth/login` (que continua exatamente como estava). Essa é a escolha que efetivamente atende a todos os requisitos simultaneamente sem tocar em `/login`, `/register` ou `/refresh`.

## Endpoints corrigidos (por herdarem de `get_current_user`)

Confirmado via inspeção do `openapi.json` gerado pela aplicação em execução (ver seção de testes abaixo) — **todo endpoint que já dependia de `get_current_user` agora aparece com o esquema `HTTPBearer` no OpenAPI**, incluindo os citados explicitamente no pedido:

- `GET /api/v1/auth/me`
- `GET /api/v1/r2/health`
- `POST /api/v1/r2/test-upload`

E também (sem exceção, todos os protegidos do sistema):

- `GET/POST /api/v1/clubs`, `GET /api/v1/clubs/{club_id}`
- `POST /api/v1/coaches`, `GET /api/v1/coaches/{coach_id}`
- `GET/POST /api/v1/goalkeepers`, `GET /api/v1/goalkeepers/{gk_id}`
- `GET/POST /api/v1/training-sessions`, `GET/PUT/DELETE /api/v1/training-sessions/{session_id}`
- `GET/POST /api/v1/videos`, `POST /api/v1/videos/upload`, `GET/PUT/DELETE /api/v1/videos/{video_id}`, `GET /api/v1/videos/{video_id}/status`
- `GET/POST /api/v1/processing-jobs`, `GET/PUT/DELETE /api/v1/processing-jobs/{job_id}`, `GET /api/v1/processing-jobs/{job_id}/status`
- `GET /api/v1/users`, `GET /api/v1/users/{user_id}`

**Permanecem públicos (corretamente, sem cadeado)**, sem nenhuma alteração de contrato:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /` e `GET /health`

## Compatibilidade com o Flutter (item 5)

O app Flutter (`ApiClient`, ver `frontend_flutter/lib/services/api_client.dart`) já envia o header exatamente como `Authorization: Bearer <token>` via interceptor do Dio — que é **exatamente** o formato que `HTTPBearer` espera e extrai. **Nenhuma alteração no frontend foi necessária ou feita.**

## Testes executados

Como não há suíte de testes automatizados no backend (`backend_fastapi/tests/` contém apenas um `__init__.py` vazio — achado já registrado no `PROJECT_ANALYSIS.md`, e `pytest` não está nem em `requirements.txt`), a validação foi feita **rodando a API de verdade**, conforme pedido no item 8:

1. **`python -m py_compile`** em todos os módulos do backend (incluindo `app/core/security.py`) — sem erros de sintaxe.
2. **API iniciada de fato** (`uvicorn app.main:app`), contra uma instância real do Postgres do projeto (`docker compose up postgres`, mesmo `docker-compose.yml` do repositório).
3. **Fluxo completo testado via HTTP real:**
   - `POST /api/v1/auth/register` → token obtido normalmente (sem alteração de contrato).
   - `GET /api/v1/auth/me` sem header → **401** (mesmo comportamento de antes).
   - `GET /api/v1/auth/me` com `Authorization: Bearer <token>` → **200**, dados do usuário retornados corretamente.
   - `GET /api/v1/r2/health` sem header → **401**.
   - `GET /api/v1/r2/health` com token → passou da autenticação e chegou à validação de credenciais R2 (**503**, porque o R2 não estava configurado neste ambiente de teste isolado — comportamento esperado e correto, confirma que a autenticação deixou de ser o bloqueio).
   - `POST /api/v1/r2/test-upload` sem header → **401**.
4. **`GET /docs`** → **200** (Swagger UI carrega normalmente).
5. **Inspeção do `GET /openapi.json`** gerado pela aplicação real em execução:
   - `components.securitySchemes.HTTPBearer` registrado como `{"type": "http", "scheme": "bearer"}`.
   - Todos os 25 endpoints protegidos listados acima aparecem com `"security": [{"HTTPBearer": []}]` na definição OpenAPI — é exatamente esse campo que faz o Swagger desenhar o cadeado por rota e aplicar o token do botão "Authorize" automaticamente a todas elas.
   - `register`/`login`/`refresh`/`/`/`health` aparecem com `"security": null` — continuam públicos.

## Achados não relacionados, encontrados durante a validação (registrados, não corrigidos)

Ao tentar subir a API real para este teste, encontrei **dois problemas pré-existentes e não relacionados a este pedido**, que impediam o servidor de iniciar com a configuração padrão do repositório. Não os corrigi, pois fogem do escopo desta tarefa (autenticação/Swagger) — apenas registro aqui para sua ciência, seguindo a mesma política já usada nas sprints anteriores:

1. **`DATABASE_URL` sem driver assíncrono**: tanto `backend_fastapi/.env` quanto `docker-compose.yml` usam `postgresql://...` (sem `+asyncpg` ou `+psycopg`). Como `app/db/base.py` usa `create_async_engine`, e `psycopg2` (driver síncrono padrão) não está em `requirements.txt`, a aplicação falha ao criar a engine com `ModuleNotFoundError: No module named 'psycopg2'`. Para validar este fix, usei `postgresql+asyncpg://...` **apenas no meu ambiente de teste local**, sem alterar nenhum arquivo do repositório.
2. **`ALLOWED_VIDEO_EXTENSIONS` no `.env`** está no formato `mp4,mov,avi,mkv` (lista separada por vírgula), mas o campo correspondente em `Settings` é tipado como `list`, e o `pydantic-settings` tenta decodificar valores de lista vindos de arquivo `.env` como **JSON** (`["mp4","mov",...]`) — o formato atual quebra com `SettingsError` ao instanciar `Settings()`. Contornei isso rodando o teste a partir de uma cópia do código sem o `.env` do projeto (usando variáveis de ambiente do processo diretamente), sem tocar no `.env` real.

Ambos os problemas, juntos, significam que **a aplicação hoje não sobe com a configuração padrão do repositório** (nem localmente, nem via `docker compose up`, pois o `docker-compose.yml` também usa `DATABASE_URL` sem driver assíncrono). Recomendo tratá-los em uma sprint dedicada — não fazem parte desta correção de autenticação e não foram alterados aqui.

## Ambiente de teste

Removido ao final da validação: parei o servidor `uvicorn` de teste e rodei `docker compose down` para remover o container/rede Postgres criados apenas para este teste (o volume `backend_fastapi_postgres_data` pode ter ficado no Docker local; rode `docker compose down -v` se quiser removê-lo também). Nenhum arquivo do projeto (`.env`, `docker-compose.yml`, etc.) foi alterado.

## Conclusão

- Único arquivo alterado: `backend_fastapi/app/core/security.py`.
- Nenhuma rota, contrato ou regra de autenticação foi alterada — apenas o **mecanismo de extração do token**, que passou do header manual (`Header(...)`) para o esquema oficial `HTTPBearer` do `fastapi.security`.
- Confirmado, com o servidor rodando de verdade, que todos os endpoints protegidos (incluindo os 3 citados explicitamente no pedido) aparecem no OpenAPI com o esquema de segurança correto, prontos para o botão "Authorize" único do Swagger.
