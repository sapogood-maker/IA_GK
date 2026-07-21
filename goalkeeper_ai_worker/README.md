# Goalkeeper AI Worker

Serviço independente de visão computacional do Goalkeeper AI. Parte do monorepo `IA_GK`, mas um sistema completamente separado do backend em runtime, dependências, configuração e banco de dados — ver `AI_WORKER_CONSTITUTION.md` (raiz do repositório), seção **Boundary Enforcement**.

## Status

**Sprint W2 — Comunicação.** O Worker agora fala de verdade com os três contratos públicos: Redis (consumer group do stream `processing_jobs`), a Worker API do backend (autenticada por `X-Worker-Api-Key` + `X-Worker-Version`) e Cloudflare R2 (geração de URLs assinadas). O Lock distribuído por vídeo (ADR-001/003) também está implementado. **Ainda não existe nenhum laço de consumo orquestrado nem processamento real de vídeo** — cada canal foi validado isoladamente; a composição em uma esteira real de Job, com retry/timeout/checkpoint, é da Sprint W3. Nenhum modelo de IA existe ainda.

## Regras de fronteira (resumo — ver documento oficial para o detalhe completo)

- Nunca importar código de `backend_fastapi/`, em nenhuma direção.
- Nunca compartilhar ambiente virtual, `requirements.txt`, configuração (`.env`/`Settings`) ou banco de dados com o backend.
- Toda comunicação futura com o backend ocorre exclusivamente via REST API, Redis e Cloudflare R2 — nunca acesso direto a Postgres/SQLAlchemy/Models/Services do backend.

Detalhes completos em `AI_WORKER_ARCHITECTURE.md`, `AI_WORKER_CONSTITUTION.md` e `DOMAIN_ARCHITECTURE.md`, na raiz do repositório.

## Ambiente

Requer Python 3.10+. Ambiente virtual e dependências são inteiramente próprios deste subprojeto — nunca reutilizar o venv/`requirements.txt` do backend.

```
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e ajuste os valores antes de executar.

## Executar

```
python -m worker.main
```

O processo inicia, registra os eventos de inicialização, aguarda um sinal de encerramento (`Ctrl+C` ou `SIGTERM`) e finaliza graciosamente.

## Testes

```
pytest
```

## Estrutura

```
worker/
├── main.py                       # ponto de entrada; ainda so aguarda o sinal de encerramento (W1)
├── config/                        # configuracao centralizada, carregada do .env - nunca hardcoded
├── observability/                  # configuracao de logging estruturado
├── core/                            # ciclo de vida do processo e excecoes proprias
├── contracts/                       # contratos publicos do Backend (REST + mensagem do Redis Stream)
├── infrastructure/                   # clientes de infraestrutura externa, agrupados por sistema
│   ├── redis/                         # cliente Redis, consumer group, Lock por video (ADR-001/003)
│   ├── backend_client/                 # cliente HTTP da Worker API (camada generica + endpoints)
│   └── storage/                         # reservado (Sprint W3) - download/upload REAL via URL assinada
└── models/                            # reservado (Sprint W4+) - Model Registry e Plugins de IA
```

`models/` e `infrastructure/storage/` existem como pacotes vazios propositalmente nesta sprint.
