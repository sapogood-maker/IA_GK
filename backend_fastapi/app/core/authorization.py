"""Autorizacao (RBAC + isolamento por clube/tenant).

Complementa app/core/security.py (que so cuida de autenticacao - quem e o
usuario). Aqui decidimos o que esse usuario pode acessar.

Regra central: SYSTEM_ADMIN acessa tudo; qualquer outro papel (CLUBE,
TREINADOR, ANALISTA) acessa exclusivamente os dados do proprio clube
(current_user.club_id). Nenhum papel alem de SYSTEM_ADMIN pode ver dados de
outro clube.
"""
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.base import get_db
from app.models.models import User, UserRole, Goalkeeper, TrainingSession, Video, ProcessingJob


def is_admin(user: User) -> bool:
    return user.role == UserRole.SYSTEM_ADMIN.value


def require_roles(*roles: UserRole):
    """Dependencia que exige que o usuario autenticado tenha um dos papeis
    informados. Uso: Depends(require_roles(UserRole.SYSTEM_ADMIN))."""
    allowed = {r.value for r in roles}

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return current_user

    return _dependency


def ensure_club_access(current_user: User, resource_club_id: UUID | None) -> None:
    """Levanta 403 se o usuario nao-admin nao pertencer ao clube dono do
    recurso. Chamar depois de já ter confirmado que o recurso existe (404)."""
    if is_admin(current_user):
        return
    if resource_club_id is None or current_user.club_id != resource_club_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to a different club",
        )


def effective_club_scope(current_user: User) -> UUID | None:
    """Retorna o club_id que deve limitar uma consulta de listagem, ou None
    se o usuario e SYSTEM_ADMIN (sem restricao)."""
    if is_admin(current_user):
        return None
    return current_user.club_id


async def resolve_club_id_for_goalkeeper(db: AsyncSession, goalkeeper_id: UUID) -> UUID | None:
    result = await db.execute(select(Goalkeeper.club_id).where(Goalkeeper.id == goalkeeper_id))
    return result.scalar_one_or_none()


async def resolve_club_id_for_training_session(db: AsyncSession, session_id: UUID) -> UUID | None:
    result = await db.execute(
        select(Goalkeeper.club_id)
        .join(TrainingSession, TrainingSession.goalkeeper_id == Goalkeeper.id)
        .where(TrainingSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def resolve_club_id_for_video(db: AsyncSession, video_id: UUID) -> UUID | None:
    result = await db.execute(
        select(Goalkeeper.club_id)
        .join(TrainingSession, TrainingSession.goalkeeper_id == Goalkeeper.id)
        .join(Video, Video.training_session_id == TrainingSession.id)
        .where(Video.id == video_id)
    )
    return result.scalar_one_or_none()


async def resolve_club_id_for_processing_job(db: AsyncSession, job_id: UUID) -> UUID | None:
    result = await db.execute(
        select(Goalkeeper.club_id)
        .join(TrainingSession, TrainingSession.goalkeeper_id == Goalkeeper.id)
        .join(Video, Video.training_session_id == TrainingSession.id)
        .join(ProcessingJob, ProcessingJob.video_id == Video.id)
        .where(ProcessingJob.id == job_id)
    )
    return result.scalar_one_or_none()
