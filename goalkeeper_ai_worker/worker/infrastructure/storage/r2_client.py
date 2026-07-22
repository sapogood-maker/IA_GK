"""Download/upload de bytes via URL assinada do Cloudflare R2 (Sprint W3).

O Worker nunca tem credenciais mestras do R2 (Boundary Enforcement) - todo
acesso passa por uma URL ja assinada, obtida via BackendClient
(`get_download_url`/`get_artifact_upload_url`). Aqui e so o HTTP GET/PUT
simples contra essa URL, sem nenhum SDK do S3.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from worker.core.exceptions import StorageError


async def download_to_path(
    url: str, dest_path: Path, transport: httpx.BaseTransport | None = None
) -> None:
    """Baixa o conteudo de uma URL assinada para um arquivo local."""
    try:
        async with httpx.AsyncClient(timeout=60.0, transport=transport) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
    except httpx.HTTPError as exc:
        raise StorageError(f"Falha ao baixar de {url}: {exc}") from exc


async def upload_file(
    url: str, file_path: Path, content_type: str, transport: httpx.BaseTransport | None = None
) -> None:
    """Envia o conteudo de um arquivo local para uma URL assinada (PUT)."""
    try:
        content = file_path.read_bytes()
        async with httpx.AsyncClient(timeout=60.0, transport=transport) as client:
            response = await client.put(url, content=content, headers={"Content-Type": content_type})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise StorageError(f"Falha ao enviar para {url}: {exc}") from exc
