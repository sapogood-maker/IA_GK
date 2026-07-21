from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import CoachCreate, CoachResponse
from app.repositories.repositories import CoachRepository
from app.core.security import get_current_user
from app.core.authorization import require_roles, is_admin, COMMON_ERROR_RESPONSES
from app.models.models import User, UserRole

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"],
    dependencies=[Depends(get_current_user)],
    responses=COMMON_ERROR_RESPONSES,
)


@router.post(
    "",
    response_model=CoachResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.CLUBE))],
)
async def create_coach(
    coach_data: CoachCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vincular um treinador a um clube. Restrito a SYSTEM_ADMIN ou ao papel
    CLUBE do proprio clube informado."""
    if not is_admin(current_user) and coach_data.club_id != current_user.club_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    coach_repo = CoachRepository(db)
    return await coach_repo.create(user_id=coach_data.user_id, club_id=coach_data.club_id)


@router.get("/{coach_id}", response_model=CoachResponse)
async def get_coach(
    coach_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    coach_repo = CoachRepository(db)
    coach = await coach_repo.get_by_id(coach_id)
    if not coach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
    if not is_admin(current_user) and coach.club_id != current_user.club_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return coach
