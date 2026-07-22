"""CleanupStage: remove o workspace temporario - roda mesmo apos falha (finally)."""
from __future__ import annotations

from worker.state.pipeline_state import PipelineState
from worker.workspace.manager import WorkspaceManager


class CleanupStage:
    """Unica responsabilidade: limpar o workspace, se ele chegou a existir."""

    def __init__(self, workspace_manager: WorkspaceManager) -> None:
        self._workspace_manager = workspace_manager

    async def run(self, state: PipelineState) -> PipelineState:
        if state.workspace_dir is not None:
            self._workspace_manager.cleanup(state.workspace_dir)
        return state
