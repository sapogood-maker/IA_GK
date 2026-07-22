"""PrepareWorkspaceStage: cria o diretorio de trabalho temporario do Job."""
from __future__ import annotations

from worker.state.pipeline_state import PipelineState
from worker.workspace.manager import WorkspaceManager


class PrepareWorkspaceStage:
    """Unica responsabilidade: criar o workspace temporario, via tempfile."""

    def __init__(self, workspace_manager: WorkspaceManager) -> None:
        self._workspace_manager = workspace_manager

    async def run(self, state: PipelineState) -> PipelineState:
        state.workspace_dir = self._workspace_manager.create(state.job_id)
        return state
