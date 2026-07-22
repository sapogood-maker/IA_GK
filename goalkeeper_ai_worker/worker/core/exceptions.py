"""Excecoes proprias do Worker.

Nunca reutiliza tipos de excecao do backend (Boundary Enforcement) -
mesmo excecoes genericas de configuracao/infraestrutura sao definidas de
forma independente aqui.
"""


class WorkerError(Exception):
    """Excecao base para todos os erros do Goalkeeper AI Worker."""


class ConfigurationError(WorkerError):
    """Configuracao ausente, invalida ou incompleta."""


class QueueConnectionError(WorkerError):
    """Falha ao conectar ou operar no Redis - fila de Jobs (stream `processing_jobs`)
    ou Lock distribuido por video, que reside no mesmo Redis."""


class BackendUnavailableError(WorkerError):
    """A Worker API do backend nao respondeu (rede/timeout/conexao)."""


class BackendRequestError(WorkerError):
    """A Worker API do backend respondeu com um erro (status >= 400)."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Backend request failed ({status_code}): {detail}")


class StorageError(WorkerError):
    """Falha ao baixar ou enviar bytes via URL assinada do Cloudflare R2."""


class PipelineError(WorkerError):
    """Falha de negocio dentro de um Stage do Pipeline (Sprint W3) - por
    exemplo, um Job inconsistente ou ja em estado terminal."""
