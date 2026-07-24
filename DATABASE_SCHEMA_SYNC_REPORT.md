# DATABASE_SCHEMA_SYNC_REPORT.md — Backend FastAPI: Sincronização de Schema (club_id + DuplicateTable)

> Escopo: diagnosticar e corrigir, pela via oficial de migrations (Alembic), dois erros encadeados em produção (Coolify): `500 Internal Server Error` em `/auth/register`/`/auth/login` (`UndefinedColumnError: column users.club_id does not exist`) e, após a primeira tentativa de correção, `DuplicateTable: relation "users" already exists` ao tentar rodar `alembic upgrade head`. Nenhum dado apagado, nenhuma tabela recriada, nenhuma coluna adicionada manualmente — tudo resolvido via o fluxo oficial do Alembic (`stamp` + migrations), com o diagnóstico completo feito **antes** de qualquer ação corretiva, conforme exigido.

## Diagnóstico completo (dados reais do banco de produção)

| Verificação | Resultado |
|---|---|
| Tabela `alembic_version` existe? | **Não** (`exists: f`; `SELECT * FROM alembic_version` retorna `relation does not exist`) |
| Tabelas existentes | Todas as 12: `users, clubs, coaches, goalkeepers, training_sessions, videos, processing_jobs, analyses, events, metrics, artifacts, reports` |
| `users` | 7 colunas, **sem `club_id`** |
| `videos.upload_status` | `USER-DEFINED`, `udt_name = uploadstatus` (ENUM nativo, **não convertido**) |
| `processing_jobs.status` | `USER-DEFINED`, `udt_name = processingjobstatus` (ENUM nativo, **não convertido**) |
| `videos` — colunas de R2 (`original_filename`, `mime_type`, `file_size_bytes`, `r2_bucket`, `r2_url`, `uploaded_at`) | **Presentes** |
| `processing_jobs` — colunas (`job_type`, `worker_id`, `retry_count`) | **Presentes** |
| `ix_users_email` | **Ainda existe** (migration `005` nunca rodou) |
| Tabelas de IA da migration `004` (`analyses/events/metrics/artifacts/reports`) | **Já existiam** |

## Causa raiz — por que o Alembic acreditou estar na revisão inicial

O histórico do git confirma: `app/main.py` chamava `Base.metadata.create_all()` no startup desde o primeiro commit (8 jun) até ser removido na auditoria da Sprint 6 (20 jul, commit `40ed065`, mesmo commit que introduziu `alembic upgrade head` no `docker-compose.yml`). Durante essas ~6 semanas, o schema de produção no Coolify foi criado inteiramente por `create_all()` — que gera tabelas diretamente a partir dos models SQLAlchemy, **sem nunca criar `alembic_version`**.

A tabela `alembic_version` só é criada pelo próprio Alembic na primeira vez que ele roda com sucesso contra um banco. Como o `Dockerfile` puro (usado pelo Coolify) nunca invocava `alembic upgrade head` — só o `command:` do `docker-compose.yml` local fazia isso —, o Alembic nunca tinha rodado contra esse banco até a minha primeira correção (adicionar o `entrypoint.sh`). Nessa primeira execução real, sem `alembic_version`, o Alembic assumiu "revisão: base" (nada aplicado) e tentou repetir a `001_initial_schema` do zero, incluindo `CREATE TABLE users` — que já existia. Daí o `DuplicateTable`.

## Por que a migration `004` sozinha (mesmo com o banco corretamente stampado) ainda falharia

A migration `004` ("Add multi-tenancy authorization and AI data model") faz duas coisas independentes no mesmo arquivo: adiciona `users.club_id` **e** cria as 5 tabelas de IA. O diagnóstico mostrou que as tabelas de IA **já existiam** (criadas por `create_all()` num momento em que os models já tinham essas classes, mas ainda não tinham `club_id` nem a conversão de enum). Ou seja, `004` estava **parcialmente satisfeita**: a parte das tabelas de IA já estava lá; a parte de `club_id` e da conversão enum→varchar, não. Rodar `004` do jeito original (sem checagem) tentaria recriar `analyses` etc. e falharia de novo, só que numa tabela diferente.

## Qual é a revisão real do banco

**Nenhuma revisão isolada representa o estado real** — é um estado híbrido entre `003` e `004` (tabelas de `004` presentes, mas não as mudanças de `004` em `users`/`videos`/`processing_jobs`). Isso é esperado: o banco nunca foi criado seguindo a sequência de migrations, foi criado por `create_all()` num ponto específico e arbitrário da evolução dos models.

## Correção aplicada — dois passos, ambos oficiais

### 1. Migration `004` tornada idempotente (código, já commitado)

Cada bloco de `004` agora verifica o estado real do banco (via `sa.inspect()`/`information_schema`) antes de agir — cria `club_id`/converte os enums/cria as tabelas de IA **somente se ainda não existirem**. Em qualquer banco onde nada disso existe (um ambiente novo, CI, ou dev local rodando as migrations desde o início), o comportamento é **idêntico** a antes — só passa a pular o que já estiver lá. `downgrade()` não foi alterado.

### 2. Um comando `alembic stamp`, uma única vez, contra o banco de produção

Isso é necessário porque a migration `001` (e `002`/`003`) **não são** idempotentes — sem marcar o banco numa revisão que já reflita a realidade, o Alembic ainda tentaria recriar `users` do zero antes de sequer chegar em `004`.

```
alembic stamp 003
```

**Por que `003` e não `004`**: meu diagnóstico (tabela acima) confirma que tudo o que `001`+`002`+`003` produzem já está fisicamente presente e correto. `004` **não** está — falta `club_id` e a conversão de enum. Marcar o banco em `003` (o último ponto genuinamente 100% satisfeito) e então deixar o `alembic upgrade head` normal aplicar `004` (agora idempotente, então só faz o que realmente falta) e `005` é a forma correta e completa de fechar a lacuna.

**Por que este comando é seguro**:
- `alembic stamp` **nunca executa DDL nem toca em dados** — só escreve/atualiza uma linha na tabela de controle `alembic_version`. É o mecanismo oficial e documentado do próprio Alembic exatamente para este cenário (banco cujo schema real não corresponde ao seu histórico de migrations rastreado).
- Depois do `stamp`, o próximo `alembic upgrade head` (já disparado automaticamente pelo `entrypoint.sh` a cada início do container) só aplica **exatamente** o que falta: adiciona `club_id` (+ índice + FK + check constraint), converte os dois enums para VARCHAR (incluindo a atualização de vocabulário `PENDING→QUEUED`), e remove o índice redundante `ix_users_email`. Nenhuma tabela é recriada, nenhum dado é apagado.

## Validação realizada (reproduzindo o cenário exato, com dados reais preservados)

1. Reproduzi o estado exato de produção num Postgres isolado e descartável: rodei `001`+`002` normalmente, depois ajustei manualmente para bater 100% com o diagnóstico (removi a coluna fantasma `size_bytes` — ver nota abaixo —, adicionei as colunas de R2, converti `upload_status`/`status` para os ENUMs nativos observados, criei as 5 tabelas de IA, removi `alembic_version`).
2. **Inseri um usuário real** (`role=system_admin`) nessa base, para provar preservação de dados através de todo o processo.
3. Confirmei a falha original: `alembic upgrade head` (com a migration `004` **antes** da correção) reproduziu **exatamente** `DuplicateTable: relation "users" already exists` — mesma mensagem do ambiente real.
4. Confirmei rollback limpo (a transação falhada não deixou nada pela metade — `alembic_version` continuou inexistente, o usuário preexistente continuou lá).
5. Apliquei a correção: `alembic stamp 003` seguido de `alembic upgrade head` (já com a migration `004` idempotente) — **sucesso, sem erros**:
   ```
   Running upgrade 003 -> 004, Add multi-tenancy authorization and AI data model
   Running upgrade 004 -> 005, Drop redundant index on users.email
   ```
6. Confirmei o estado final: `users.club_id` presente (com índice, FK e check constraint), `upload_status`/`status` agora `varchar` (os dois ENUMs antigos foram removidos do banco), `ix_users_email` removido, `alembic_version = 005` (head).
7. **O usuário inserido antes da correção continuou intacto** (`SELECT * FROM users` mostrou o mesmo `id`/`name`/`email`/`role`, agora com `club_id NULL` — permitido porque `role='system_admin'`).
8. **Idempotência**: rodei `alembic upgrade head` de novo — no-op, sem erro.
9. **Caminho "fresh" (banco vazio, nunca tocado)**: confirmei que `001→002→003→004→005` roda de ponta a ponta exatamente como antes, sem nenhuma mudança de comportamento — a idempotência de `004` só entra em ação quando os objetos já existem.
10. **API real, contra o banco corrigido**: subi o container real do backend apontando para esse banco.
    - `POST /auth/register` sem `club_id` → `400 "club_id is required for this role"` (validação normal, não mais `500`).
    - `POST /auth/login` do usuário preexistente com senha errada → `401 "Invalid credentials"` (não mais `500`).
    - `POST /auth/register` com um `club_id` real → `200 OK`, token emitido.
11. Suíte completa de testes automatizados do backend: **48 passed**, sem nenhuma regressão.

## Achado paralelo, documentado mas **não corrigido** nesta sprint

A migration `002` declara uma coluna `videos.size_bytes` (Integer) que **não existe** em produção e **não existe** no model atual (`app/models/models.py` só tem `file_size_bytes`). Isso é uma inconsistência histórica na própria migration `002` (aparentemente a coluna foi renomeada no código antes de qualquer migration formal existir), inofensiva hoje porque produção nunca teve essa coluna — mas significa que um banco **totalmente novo**, migrado do zero via `alembic upgrade head`, ganharia uma coluna `size_bytes` órfã (nunca lida/escrita pela aplicação). Não alterei a migration `002` (evitar reescrever uma migration histórica que pode já ter rodado em outros ambientes) — fica registrado aqui como item de limpeza futura, não bloqueia nada do fluxo atual.

## Comando a ser executado no ambiente remoto (Coolify)

Com o código já commitado/enviado (migration `004` idempotente), falta um único passo manual, uma única vez, direto no Postgres do Coolify:

```sql
-- Rodar com o mesmo usuário/acesso usado nas queries de diagnóstico
```
```
alembic stamp 003
```
(via terminal do container do backend no Coolify, ex.: `docker exec -it <container> alembic stamp 003` — ou o equivalente que o Coolify oferecer para rodar um comando dentro do container do backend)

Depois disso, um redeploy/restart normal do serviço já aplica o resto automaticamente (o `entrypoint.sh` roda `alembic upgrade head`, que agora só faz o que genuinamente falta). Revalidar em seguida:
```
POST http://hs00sw0cwcksgc080okossk4.191.5.53.184.sslip.io/api/v1/auth/register
POST http://hs00sw0cwcksgc080okossk4.191.5.53.184.sslip.io/api/v1/auth/login
```
Ambos devem responder `200`/`400`/`401` conforme o caso — nunca mais `500`.

## Versão final do schema (validado local, idêntico ao que o comando acima produzirá em produção)

```
users:
  id, name, email (unique), password_hash, role, created_at, updated_at,
  club_id (uuid, nullable, FK -> clubs.id ON DELETE SET NULL, indexed)
  CHECK (role = 'system_admin' OR club_id IS NOT NULL)

videos.upload_status:       varchar (era ENUM uploadstatus)
processing_jobs.status:     varchar (era ENUM processingjobstatus)
ix_users_email:              removido (redundante com a UNIQUE constraint)

alembic_version: 005 (head)
```

Byte-a-byte compatível com `app/models/models.py`.
