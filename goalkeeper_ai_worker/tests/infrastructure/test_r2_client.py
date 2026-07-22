"""Testes de worker.infrastructure.storage.r2_client - HTTP mockado (httpx.MockTransport)."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from worker.core.exceptions import StorageError
from worker.infrastructure.storage.r2_client import download_to_path, upload_file


async def test_download_to_path_writes_the_response_bytes(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"bytes-de-teste")

    dest = tmp_path / "downloaded.bin"
    await download_to_path("https://fake-r2.test/video.bin", dest, transport=httpx.MockTransport(handler))

    assert dest.read_bytes() == b"bytes-de-teste"


async def test_download_to_path_raises_storage_error_on_http_failure(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    dest = tmp_path / "downloaded.bin"
    with pytest.raises(StorageError):
        await download_to_path("https://fake-r2.test/missing.bin", dest, transport=httpx.MockTransport(handler))


async def test_upload_file_sends_the_file_content(tmp_path: Path) -> None:
    source = tmp_path / "artifact.json"
    source.write_text('{"a": 1}', encoding="utf-8")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = request.content
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(200)

    await upload_file(
        "https://fake-r2.test/artifact.json", source, "application/json", transport=httpx.MockTransport(handler)
    )

    assert captured["content"] == source.read_bytes()
    assert captured["content_type"] == "application/json"


async def test_upload_file_raises_storage_error_on_http_failure(tmp_path: Path) -> None:
    source = tmp_path / "artifact.json"
    source.write_text("{}", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(StorageError):
        await upload_file(
            "https://fake-r2.test/artifact.json", source, "application/json", transport=httpx.MockTransport(handler)
        )
