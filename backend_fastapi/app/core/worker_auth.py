"""Autenticacao do AI Worker (service account).

Mecanismo completamente separado da autenticacao de usuario humano
(app/core/security.py, JWT/HTTPBearer). O Worker nao e um "usuario" - e uma
identidade de maquina, autenticada por uma API Key de longa duracao enviada
no header "X-Worker-Api-Key".

Regra de separacao (AI_WORKER_ARCHITECTURE.md secao 6, SPRINT7_REPORT.md):
- Endpoints do Worker (app/api/v1/worker.py) SO aceitam X-Worker-Api-Key.
  Um JWT de usuario valido NAO funciona neles.
- Endpoints humanos (todos os outros) SO aceitam JWT via Authorization:
  Bearer. Uma API Key valida NAO funciona neles.
Os dois mecanismos nunca sao combinados no mesmo router.
"""
from fastapi import Header, HTTPException, status
from typing import Optional

from app.core.config import get_settings


async def require_worker_api_key(x_worker_api_key: Optional[str] = Header(default=None)) -> None:
    """Dependencia que exige a API Key do Worker no header X-Worker-Api-Key.

    Fail-closed: se WORKER_API_KEY nao estiver configurado no ambiente,
    nenhuma chave e aceita (nao ha um "modo aberto" por omissao)."""
    settings = get_settings()

    if not settings.worker_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker authentication is not configured on this server",
        )

    if not x_worker_api_key or x_worker_api_key != settings.worker_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Worker-Api-Key header",
        )
