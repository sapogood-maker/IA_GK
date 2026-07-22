"""Testes de worker.workspace.manager.WorkspaceManager - sistema de arquivos
real (tempfile), sem nenhuma dependencia de rede."""
from __future__ import annotations

import tempfile
from pathlib import Path

from worker.workspace.manager import WorkspaceManager


def test_create_returns_an_existing_directory_under_the_system_tempdir() -> None:
    manager = WorkspaceManager()
    workspace_dir = manager.create("job-1")

    try:
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()
        assert str(Path(tempfile.gettempdir())) in str(workspace_dir)
    finally:
        manager.cleanup(workspace_dir)


def test_create_isolates_different_jobs_in_different_directories() -> None:
    manager = WorkspaceManager()
    dir_a = manager.create("job-a")
    dir_b = manager.create("job-b")

    try:
        assert dir_a != dir_b
    finally:
        manager.cleanup(dir_a)
        manager.cleanup(dir_b)


def test_cleanup_removes_the_directory_and_its_contents() -> None:
    manager = WorkspaceManager()
    workspace_dir = manager.create("job-2")
    (workspace_dir / "artifact.json").write_text("{}", encoding="utf-8")

    manager.cleanup(workspace_dir)

    assert not workspace_dir.exists()


def test_cleanup_does_not_raise_if_directory_already_removed() -> None:
    manager = WorkspaceManager()
    workspace_dir = manager.create("job-3")
    manager.cleanup(workspace_dir)

    manager.cleanup(workspace_dir)
