from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, clubs, coaches, goalkeepers, training_sessions, videos, processing_jobs
from app.db.base import engine, Base

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


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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
