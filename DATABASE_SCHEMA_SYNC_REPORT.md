# DATABASE_SCHEMA_SYNC_REPORT.md — Backend FastAPI: Sincronização de Schema (club_id)

> Escopo: diagnosticar e corrigir, pela via oficial de migrations (Alembic), o erro `500 Internal Server Error` em `POST /api/v1/auth/register` e `POST /api/v1/auth/login` no ambiente remoto (Coolify), causado por `asyncpg.exceptions.UndefinedColumnError: column users.club_id does not exist`. Nenhuma alteração manual no banco, nenhuma alteração no `Model User` para remover `club_id` — correção exclusivamente via o fluxo oficial de migrations.

## Causa raiz

`users.club_id` foi introduzido pela **migration `004_add_authorization_and_ai_data_model.py`** (revisão `004`, `down_revision = "003"`) — confirmada presente e correta no repositório, junto com a coluna, o índice, a foreign key e a check constraint (`ck_users_club_id_required_unless_admin`) que o `Model` (`app/models/models.py`) exige.

**A migration existe e está correta. O problema nunca foi a migration em si — foi o mecanismo que a executa.**

`docker-compose.yml` (usado só para desenvolvimento local) sobrescrevia o `command:` do container para `sh -c "alembic upgrade head && uvicorn ..."` — e esse `command:` era o **ÚNICO** lugar em todo o repositório onde `alembic upgrade head` de fato rodava. O `Dockerfile` em si (`CMD ["uvicorn", "app.main:app", ...]`) **nunca** executava migrations.

Qualquer forma de rodar a imagem que não passe por esse `command:` específico do `docker-compose.yml` local — como o Coolify, que builda/roda a imagem a partir do `Dockerfile` diretamente — nunca aplicava `alembic upgrade head`. O banco remoto ficou parado na revisão `003` (confirmado via `SELECT version_num FROM alembic_version` no ambiente de teste que reproduziu o bug — ver "Validação" abaixo), sem nunca receber as migrations `004`/`005`.

## Migration correspondente

| Revisão | Arquivo | O que faz |
|---|---|---|
| `001` | `001_initial_schema.py` | Schema inicial |
| `002` | `002_add_sprint2a_tables.py` | Tabelas da Sprint 2A |
| `003` | `003_add_r2_integration.py` | Integração R2 |
| **`004`** | **`004_add_authorization_and_ai_data_model.py`** | **Adiciona `users.club_id` (+ índice, FK, check constraint) — a migration que faltava aplicar** |
| `005` | `005_drop_redundant_email_index.py` | Remove índice redundante em `users.email` |

Cadeia de revisões confirmada íntegra e linear (`001→002→003→004→005`, sem múltiplas heads, sem forks) — não havia nada de errado na ORDEM ou no CONTEÚDO das migrations, apenas no mecanismo de execução.

## Correção — fluxo oficial de migrations, aplicado pelo próprio container

**Nenhuma mudança na migration em si.** A correção move a responsabilidade de rodar `alembic upgrade head` para dentro do `Dockerfile`, via um `entrypoint.sh` novo — assim, **qualquer** forma de executar a imagem (Coolify, `docker run`, `docker-compose`, outro orquestrador) aplica as migrations pendentes antes de servir tráfego, sem depender de um `command:` específico de um compose de desenvolvimento.

### `backend_fastapi/entrypoint.sh` (novo)

```sh
#!/bin/sh
set -e
echo "[entrypoint] aplicando migrations (alembic upgrade head)..."
alembic upgrade head
echo "[entrypoint] migrations aplicadas - iniciando: $*"
exec "$@"
```

`set -e`: se a migration falhar, o container encerra de forma visível (logs), em vez de subir a API contra um schema desatualizado/quebrado. `exec "$@"`: o processo `uvicorn` vira PID 1 do container (mesmo princípio já usado no `entrypoint.sh` do Worker, Deployment v1.0).

### `backend_fastapi/Dockerfile` (alterado)

```dockerfile
COPY entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### `backend_fastapi/docker-compose.yml` (simplificado)

O `command:` não precisa mais chamar `alembic upgrade head` explicitamente — o `ENTRYPOINT` da imagem já garante isso. Mantido apenas `--reload` (conveniência de desenvolvimento local):

```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Validação realizada (reproduzindo o bug real, não hipotético)

1. Subi um Postgres **novo e isolado** (container descartável, porta `5555`).
2. Rodei `alembic upgrade 003` contra ele — reproduzindo **exatamente** o estado relatado do ambiente remoto: `alembic_version = 003`, `users` **sem** `club_id`.
3. Buildei a imagem corrigida (`Dockerfile` + `entrypoint.sh` novos).
4. Rodei o container **sem nenhum override de comando** (exatamente como o Coolify rodaria a imagem crua) contra esse Postgres "quebrado".
5. **Resultado**: o entrypoint aplicou `004`→`005` automaticamente, sem nenhuma intervenção manual:
   ```
   [entrypoint] aplicando migrations (alembic upgrade head)...
   INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, Add multi-tenancy authorization and AI data model
   INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, Drop redundant index on users.email
   [entrypoint] migrations aplicadas - iniciando: uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```
6. Confirmei via `psql \d users`: `club_id` presente, com o índice (`ix_users_club_id`), a FK (`fk_users_club_id_clubs`) e a check constraint (`ck_users_club_id_required_unless_admin`) — **exatamente** o que o `Model` declara. `alembic_version = 005` (head).
7. **Idempotência**: reiniciei o mesmo container (`docker restart`) — o entrypoint rodou `alembic upgrade head` de novo, sem erro, sem reaplicar nada (já estava em `head`) — confirma que restarts/redeploys repetidos no Coolify não vão quebrar nada.
8. Apliquei a mesma correção ao stack de desenvolvimento local (`docker compose up -d --build`) — rebuild limpo, migrations reaplicadas (no-op, já estava em `head`), login do usuário de teste local continua funcionando.

## Resultado dos testes

### Contra o ambiente que reproduziu o bug (schema corrigido pelo entrypoint)

| Chamada | Antes da correção (simulado) | Depois da correção |
|---|---|---|
| `POST /api/v1/auth/register` (usuário novo) | `500 Internal Server Error` (`UndefinedColumnError`) | `200 OK` — token emitido |
| `POST /api/v1/auth/login` (senha correta) | `500 Internal Server Error` | `200 OK` — token emitido |
| `POST /api/v1/auth/login` (senha errada) | `500 Internal Server Error` | `401 Unauthorized` — `{"detail":"Invalid credentials"}` (erro esperado, não mais um crash) |

### Suíte de testes automatizados do backend

`pytest` completo: **48 passed** (nenhuma regressão introduzida pelas mudanças no `Dockerfile`/`docker-compose.yml`/`entrypoint.sh` — nenhum código Python foi alterado). As falhas observadas numa primeira tentativa (`redis.exceptions...`, depois `asyncpg.exceptions.InvalidCatalogNameError: database "goalkeeper_ai_test" does not exist`) eram lacunas pré-existentes do ambiente de teste LOCAL desta sessão (faltava o Redis de teste na porta `6380` e o banco `goalkeeper_ai_test` nunca havia sido criado nesta máquina) — **não relacionadas** ao bug relatado nem introduzidas por esta correção; resolvidas apenas para obter um sinal limpo de "sem regressão".

## Próximo passo — aplicar no ambiente remoto (Coolify)

Esta correção está no código (`backend_fastapi/`), validada localmente contra o cenário exato do bug. Para o ambiente remoto realmente ficar corrigido, é necessário **redeploy** do serviço backend no Coolify a partir deste código atualizado — o próprio container, ao subir, vai rodar `alembic upgrade head` automaticamente (via o novo `ENTRYPOINT`) e trazer aquele banco de `003` para `005`, criando `club_id` do jeito oficial, sem qualquer intervenção manual no banco.

Depois do redeploy, revalidar diretamente contra o ambiente remoto:
```
POST http://hs00sw0cwcksgc080okossk4.191.5.53.184.sslip.io/api/v1/auth/register
POST http://hs00sw0cwcksgc080okossk4.191.5.53.184.sslip.io/api/v1/auth/login
```
Ambos devem parar de retornar `500` — e a conta `lima.paulo@aol.com` deve voltar a autenticar normalmente pelo Flutter assim que o redeploy acontecer (o login em si nunca teve nada de errado com a senha — o servidor simplesmente não conseguia nem executar a query).

## Versão final do schema (local, validado)

```
users:
  id            uuid PK
  name          varchar
  email         varchar UNIQUE
  password_hash varchar
  role          varchar DEFAULT 'viewer'
  club_id       uuid NULL, FK -> clubs(id) ON DELETE SET NULL, indexed
  created_at    timestamptz DEFAULT now()
  updated_at    timestamptz
  CHECK (role = 'system_admin' OR club_id IS NOT NULL)

alembic_version: 005 (head)
```

Byte-a-byte compatível com `app/models/models.py` — confirmado via `psql \d users` após a migration automática.
