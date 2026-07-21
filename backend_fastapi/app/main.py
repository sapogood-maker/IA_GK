from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, clubs, coaches, goalkeepers, training_sessions, videos, processing_jobs, r2, worker
from app.core.config import get_settings
import logging

# Sem isso, o nivel padrao do logger raiz do Python (WARNING) descarta
# silenciosamente TODO logger.info(...) do projeto - inclusive os logs
# estruturados de publicacao na fila (app/core/queue.py) e de upload
# (video_upload_service.py). Achado real durante a validacao da Sprint 7
# (nenhum logger.info aparecia no `docker logs`, desde o inicio do
# projeto) - ver SPRINT7_REPORT.md.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Goalkeeper AI API",
    description="API for futsal goalkeeper scouting and training analysis",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(clubs.router)
app.include_router(coaches.router)
app.include_router(goalkeepers.router)
app.include_router(training_sessions.router)
app.include_router(videos.router)
app.include_router(processing_jobs.router)
app.include_router(r2.router)
app.include_router(worker.router)
app.include_router(worker.admin_router)


@app.on_event("startup")
async def startup():
    # O schema do banco e gerenciado exclusivamente pelo Alembic (fluxo
    # oficial unico - ver SPRINT6_REPORT.md). A aplicacao nao cria/altera
    # tabelas em runtime; rode "alembic upgrade head" antes de iniciar o
    # servidor (ja integrado ao comando do container no docker-compose.yml).

    # Validate required R2 environment variables
    settings = get_settings()
    missing_vars = []
    
    if not settings.r2_account_id:
        missing_vars.append("R2_ACCOUNT_ID")
    if not settings.r2_access_key_id:
        missing_vars.append("R2_ACCESS_KEY_ID")
    if not settings.r2_secret_access_key:
        missing_vars.append("R2_SECRET_ACCESS_KEY")
    if not settings.r2_bucket_name:
        missing_vars.append("R2_BUCKET_NAME")
    
    if missing_vars:
        logger.warning(
            f"Missing R2 configuration: {', '.join(missing_vars)}. "
            f"R2 features will not be available. "
            f"Configure these environment variables to enable R2 integration."
        )
    else:
        logger.info("R2 configuration validated. R2 features are available.")


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "Goalkeeper AI API"}


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "Goalkeeper AI API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
