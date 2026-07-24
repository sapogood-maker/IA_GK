#!/bin/sh
# Entrypoint do container do backend (Goalkeeper AI API).
#
# Causa raiz corrigida por este arquivo: `alembic upgrade head` só rodava
# via o `command:` do docker-compose.yml (conveniente para dev local), mas
# o Dockerfile em si nunca garantia isso - qualquer deploy que rode a
# imagem diretamente (Coolify, `docker run`, outro orquestrador que não
# leia o `command:` do compose) nunca aplicava migrations, deixando o
# schema do banco desatualizado em relação aos models (ex.: users.club_id,
# migration 004, nunca chegou a ser criada em produção).
#
# `set -e`: se a migration falhar, o container encerra imediatamente e de
# forma visível (logs), em vez de subir a API contra um schema quebrado.
set -e

echo "[entrypoint] aplicando migrations (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] migrations aplicadas - iniciando: $*"
exec "$@"
