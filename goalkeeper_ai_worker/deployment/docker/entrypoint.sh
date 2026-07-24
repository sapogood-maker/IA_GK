#!/bin/sh
# Entrypoint do container do Goalkeeper AI Worker (Deployment v1.0).
#
# Responsabilidade unica: aguardar o Redis ficar alcancavel (worker.wait_for_redis)
# ANTES de iniciar o processo principal - nunca faz parte do Orchestrator/
# Pipeline em runtime (Secao 1/2/6 da Constituicao permanecem inalteradas).
# Reconexao APOS o startup e responsabilidade do connection pool do
# redis.asyncio + do `restart: unless-stopped` do docker-compose - ver
# DEPLOYMENT_V1_REPORT.md.
#
# `set -e`: qualquer falha aqui (ex.: Redis nunca fica disponivel dentro
# do timeout) interrompe o container imediatamente, em vez de deixar o
# Worker subir sem fila - falha rapida e visivel (`docker logs`), nao um
# processo travado silenciosamente.
set -e

echo "[entrypoint] aguardando Redis ficar alcancavel..."
python -m worker.wait_for_redis

echo "[entrypoint] Redis alcancavel - iniciando: $*"
# exec substitui o processo do shell pelo processo do Worker (PID 1) -
# essencial para que SIGTERM do `docker stop` chegue diretamente ao
# Worker (install_shutdown_handlers, worker/core/lifecycle.py) em vez de
# ser absorvido por este script.
exec "$@"
