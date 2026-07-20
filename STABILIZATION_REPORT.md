# STABILIZATION_REPORT.md — Sprint de Estabilização do Backend

> Escopo: apenas infraestrutura, configuração e compatibilidade do backend. Nenhum endpoint, contrato de API ou arquivo do frontend Flutter foi alterado. Nenhuma funcionalidade nova foi criada.

## Objetivo

Deixar o backend consistente e funcional em desenvolvimento local, Docker e (por extensão de configuração) Coolify, antes de retomar o módulo de Vídeos/IA. O ponto de partida foram dois problemas já registrados no `AUTH_FIX_REPORT.md` (encontrados de forma incidental na sprint anterior): `DATABASE_URL` sem driver assíncrono e `ALLOWED_VIDEO_EXTENSIONS` em formato incompatível com `pydantic-settings`. Ao investigar a fundo, mais três problemas de infraestrutura foram descobertos e corrigidos (ver seção 2).

## 1. Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `backend_fastapi/app/core/config.py` | `DATABASE_URL`: validador normaliza `postgres://`/`postgresql://` para `postgresql+asyncpg://` automaticamente. `ALLOWED_VIDEO_EXTENSIONS`: campo mudou de `list` para `str` (evita o bug do pydantic-settings, ver seção 2.2), com nova propriedade `allowed_video_extensions_list` para consumo |
| `backend_fastapi/app/services/video_upload_service.py` | Passa a usar `settings.allowed_video_extensions_list` em vez de `settings.allowed_video_extensions` (único consumidor do campo) |
| `backend_fastapi/alembic/env.py` | Nova função `_sync_database_url()`: deriva uma URL com driver **síncrono** (`postgresql+psycopg://`) a partir do `DATABASE_URL` assíncrono da aplicação, usada nos dois modos de migração (online/offline) |
| `backend_fastapi/alembic.ini` | Removidas seções `[loggers]`/`[logger_root]`/`[logger_sqlalchemy]`/`[logger_alembic]` **duplicadas**; removido `sqlalchemy.url_queue_strategy = lifo` (parâmetro incompatível com a versão pinada do SQLAlchemy) |
| `backend_fastapi/requirements.txt` | Removida a duplicata de `passlib[bcrypt]==1.7.4`; adicionados comentários explicando por que `psycopg` (Alembic/sync) e `asyncpg` (app/async) coexistem, e por que `bcrypt` está fixado em `4.0.1` |
| `backend_fastapi/docker-compose.yml` | Removido `version: "3.8"` (obsoleto, gerava aviso); `DATABASE_URL` do serviço `backend` corrigido para `postgresql+asyncpg://...`; adicionado `healthcheck` ao serviço `backend` |
| `backend_fastapi/.env.example` | Reescrito: `DATABASE_URL` corrigido, comentário explicativo em cada variável, **valores que pareciam credenciais reais da Cloudflare R2 substituídos por placeholders genéricos** (ver seção 4) |
| `backend_fastapi/00_START_HERE.md`, `backend_fastapi/LOCAL_SETUP.md`, `backend_fastapi/PORT_CONFIGURATION.md` | Exemplos de `DATABASE_URL` corrigidos para `postgresql+asyncpg://`, para consistência com a configuração real |
| `backend_fastapi/test_hash.py` | **Removido** — script de depuração esquecido na raiz do backend (fora de `tests/`), sem uso em nenhum lugar do projeto, que imprimia uma senha em texto puro e seu hash no console (item 9 — limpeza) |

Nenhum arquivo em `frontend_flutter/` foi tocado. Nenhum endpoint, schema Pydantic ou rota mudou de contrato.

## 2. Problemas encontrados e corrigidos

### 2.1 `DATABASE_URL` sem driver assíncrono

`docker-compose.yml`, `.env.example` e a documentação usavam `postgresql://...` (sem `+asyncpg`). Como `app/db/base.py` usa `create_async_engine`, e `psycopg2` (driver síncrono padrão do SQLAlchemy) não está instalado, a aplicação falhava com `ModuleNotFoundError: No module named 'psycopg2'` ao subir — **em qualquer ambiente**, incluindo `docker compose up`.

**Correção:** todos os locais foram atualizados para `postgresql+asyncpg://`, e `Settings.validate_database_url` agora normaliza automaticamente `postgres://`/`postgresql://` para `postgresql+asyncpg://` caso alguém configure sem o driver (comum em plataformas como Coolify/Heroku, que costumam fornecer `DATABASE_URL` nesse formato "genérico"). Isso significa que a aplicação **funciona mesmo que a variável de ambiente não inclua o driver explicitamente**.

### 2.2 `ALLOWED_VIDEO_EXTENSIONS` incompatível com `pydantic-settings`

O campo era tipado como `list`, mas o `.env` usa o formato `mp4,mov,avi,mkv` (separado por vírgula). O `pydantic-settings` tenta decodificar campos `list`/`dict` vindos de variável de ambiente como **JSON**, e `mp4,mov,avi,mkv` não é JSON válido — a aplicação quebrava com `SettingsError` já na instanciação de `Settings()`, antes mesmo de qualquer rota ser registrada.

**Correção:** o campo passou a ser `str` (não sofre a decodificação automática de tipos complexos do pydantic-settings) e uma propriedade `allowed_video_extensions_list` faz o parsing (`split(",")`, `strip()`, `lower()`) sob demanda. **Não é mais necessário alterar o `.env` manualmente** — o formato `mp4,mov,avi,mkv` já usado continua funcionando, e agora funciona de fato.

> Avaliei usar `Annotated[list, NoDecode]` (mecanismo oficial do `pydantic-settings` para desabilitar essa decodificação automática campo a campo), mas essa API só existe a partir de uma versão mais nova do `pydantic-settings` do que a pinada (`2.1.0`) — confirmado tentando importar `NoDecode` no ambiente real. Para não alterar versões de dependências sem necessidade (e arriscar outras incompatibilidades), optei pela solução compatível com a versão já usada no projeto.

### 2.3 `alembic.ini` com seções duplicadas (bloqueava o Alembic por completo)

O arquivo tinha os blocos `[loggers]`, `[logger_root]`, `[logger_sqlalchemy]` e `[logger_alembic]` **repetidos** (uma cópia antes de `[alembic]`, outra depois). O `configparser` do Python rejeita isso com `DuplicateSectionError`, impedindo **qualquer** comando `alembic` de rodar — nem `alembic upgrade head`, nem `alembic revision`, nada. Esse era um bloqueio duro para "Migrações" funcionarem, item explicitamente citado no pedido.

**Correção:** removida a cópia duplicada, mantendo um único bloco de configuração de logging.

### 2.4 `alembic.ini` com parâmetro incompatível com a versão do SQLAlchemy

Depois de corrigir o item 2.3, o Alembic ainda falhava: `sqlalchemy.url_queue_strategy = lifo` no `[alembic]` é repassado como argumento para `create_engine()`, mas esse parâmetro não existe na versão pinada do SQLAlchemy (`2.0.23`) — `TypeError: Invalid argument(s) 'url_queue_strategy'`. Provavelmente um resquício de um template gerado por uma versão mais nova de SQLAlchemy/Alembic do que a efetivamente usada no projeto.

**Correção:** linha removida.

### 2.5 Alembic usava o mesmo `DATABASE_URL` assíncrono para um engine síncrono

`alembic/env.py` cria o engine de migração com `engine_from_config` (**síncrono**), mas lê a mesma `DATABASE_URL` que a aplicação usa para o `AsyncEngine`. Com a correção do item 2.1 (`+asyncpg` em todo lugar), o Alembic passaria a tentar usar `asyncpg` — um driver **exclusivamente assíncrono** — dentro de um engine síncrono, o que não funciona.

**Correção:** nova função `_sync_database_url()` em `alembic/env.py`, que troca `+asyncpg` (ou `postgres://`) por `+psycopg` antes de configurar o engine de migração. `psycopg` (v3) já era uma dependência do projeto — confirmei que ele suporta conexão síncrona nativamente (diferente do `asyncpg`), então essa é exatamente a finalidade dessa dependência no `requirements.txt` (documentado com comentário, ver seção 1). **Um único `DATABASE_URL` continua sendo a única variável a configurar** — a app usa `+asyncpg`, o Alembic deriva `+psycopg` automaticamente, sem exigir uma segunda variável de ambiente.

### 2.6 `requirements.txt`: duplicata

`passlib[bcrypt]==1.7.4` aparecia duas vezes. Removida a duplicata.

### 2.7 Compatibilidade `passlib` + `bcrypt` (verificada, sem problema real)

Testei explicitamente `passlib==1.7.4` com `bcrypt==4.0.1` (hash + verify) — funciona sem avisos. O problema conhecido de incompatibilidade entre essas bibliotecas só existe a partir de `bcrypt>=4.1.0` (que remove o atributo `bcrypt.__about__.__version__` que o `passlib` 1.7.4 usa para detectar a versão). Como o projeto já fixa `bcrypt==4.0.1`, **não há problema real aqui** — apenas documentei isso com um comentário no `requirements.txt` para que ninguém atualize o `bcrypt` sem querer no futuro e reintroduza o problema.

### 2.8 Script de debug esquecido (`test_hash.py`)

Fora do escopo de `tests/`, sem nenhuma referência em outro lugar do projeto, imprimia uma senha em texto puro (`"Paulo@p01212"`) e seu hash bcrypt no console. Removido (item 9 do pedido).

## 3. O que foi verificado e **não** alterado (fora do escopo desta sprint)

- **`app/main.py` roda `Base.metadata.create_all` no startup, além do Alembic existir** (achado já registrado no `PROJECT_ANALYSIS.md`, item 7.6). As migrações agora **funcionam corretamente** quando executadas (seção 5), mas o `create_all` automático continua coexistindo com elas — resolver essa sobreposição é uma decisão arquitetural (ex.: remover o `create_all` e depender só de `alembic upgrade head` no entrypoint do container), não uma correção de infraestrutura pontual, e alterar esse comportamento de startup poderia ser interpretado como mudança de funcionalidade. Deixei como recomendação para a próxima sprint (seção 6).
- Rotação de credenciais Cloudflare R2 expostas no histórico do Git (achado da Sprint 0, ainda não resolvido) — fora do escopo desta sprint de infraestrutura.

## 4. Sobre os segredos no `.env.example`

O `.env.example` anterior continha valores que pareciam credenciais reais da Cloudflare R2 (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, etc.) em vez de placeholders. Como parte da revisão pedida no item 4 (comentar/organizar o `.env.example`), substituí esses valores por placeholders claros (`your-r2-access-key-id` etc.). **Isso não afeta o `.env` real do projeto** (que não foi tocado) **nem rotaciona nada na Cloudflare** — apenas impede que o arquivo de exemplo continue parecendo conter segredos reais. A rotação das credenciais em si continua sendo uma decisão sua, como já registrado anteriormente.

## 5. Testes executados

| Verificação | Resultado |
|---|---|
| `pytest` | **Não existe suíte** (`backend_fastapi/tests/` só tem `__init__.py` vazio) — nada para executar, conforme já documentado no `PROJECT_ANALYSIS.md` |
| `python -m py_compile` em todos os módulos do backend | **Sem erros de sintaxe** |
| `docker compose up --build` (do zero, sem nenhum ajuste manual) | **Sucesso** — `goalkeeper_ai_db` e `goalkeeper_ai_backend` subiram e ficaram `healthy` (novo healthcheck do backend passou) |
| Migrações Alembic (`alembic upgrade head`) contra um Postgres **novo e vazio**, isolado, usando o `DATABASE_URL` assíncrono da app | **Sucesso**: `001 → 002 → 003` aplicadas em sequência; confirmado via `\dt` (8 tabelas, incluindo `alembic_version`) e `SELECT version_num FROM alembic_version` (`003`) |
| `GET /health` | `200 {"status":"ok",...}` |
| `POST /api/v1/auth/register` + `POST /api/v1/auth/login` | `200`, tokens emitidos normalmente |
| `GET /api/v1/auth/me` sem token | `401` (comportamento correto, inalterado) |
| `GET /api/v1/auth/me` com token | `200`, dados do usuário |
| `GET /api/v1/r2/health` com token | **`200`, `read_access: true`, `write_access: true`** |
| `POST /api/v1/r2/test-upload` com token | **`200`, "R2 write access verified successfully"** |
| `openapi.json` | `HTTPBearer` continua registrado corretamente; endpoints protegidos/públicos inalterados desde o `AUTH_FIX_REPORT.md` |

### ⚠️ Nota importante sobre o teste do R2

O `docker-compose.yml` monta todo o diretório do backend como volume (`- .:/app`), então o container em execução **leu o `.env` real do seu ambiente** (com as credenciais R2 configuradas), não apenas as variáveis definidas no `docker-compose.yml`. Como resultado, `GET /r2/health` e `POST /r2/test-upload` rodaram **de verdade** contra o bucket R2 real configurado (`goalkeeper-ai-videos`), confirmando leitura, escrita e exclusão — o item 6 do pedido foi validado de forma real, não apenas simulada. O `POST /r2/test-upload` é auto-limpante por design (sobe um arquivo de teste, confirma, apaga, confirma a remoção) — não deixou nenhum arquivo residual no bucket. Acho importante deixar isso registrado com transparência, já que envolve as mesmas credenciais sensíveis mencionadas em relatórios anteriores.

Ao final de cada rodada de teste, os containers/volumes temporários foram removidos (`docker compose down`), sem deixar nada rodando em segundo plano.

## 6. Recomendações futuras

1. Decidir e resolver a sobreposição `create_all` vs. Alembic (seção 3) — provavelmente remover o `create_all` do `startup` e rodar `alembic upgrade head` no entrypoint do container.
2. Rotacionar as credenciais Cloudflare R2 expostas no histórico do Git (pendência recorrente desde a Sprint 0).
3. Considerar adicionar uma suíte mínima de testes automatizados (`pytest`) para o backend, hoje inexistente.
4. Validar a configuração completa (incluindo R2) também em um ambiente Coolify real, já que as correções aqui foram validadas em Docker local — a lógica de normalização do `DATABASE_URL` foi pensada especificamente para tolerar o formato que plataformas como Coolify costumam fornecer, mas não há como testar isso sem acesso a uma instância real.

## 7. Git

Confirmado via `git status` antes do commit: **apenas arquivos dentro de `backend_fastapi/` foram modificados/removidos** (fora ruído pré-existente de `__pycache__`/arquivos de nome corrompido, não relacionados a esta sprint e não incluídos no commit). Nenhum arquivo em `frontend_flutter/` foi tocado.
