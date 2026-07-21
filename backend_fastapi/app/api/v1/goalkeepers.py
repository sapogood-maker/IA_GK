from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import GoalkeeperCreate, GoalkeeperResponse
from app.repositories.repositories import GoalkeeperRepository
from app.core.security import get_current_user
from app.core.authorization import is_admin, effective_club_scope, COMMON_ERROR_RESPONSES
from app.models.models import User

router = APIRouter(
    prefix="/api/v1/goalkeepers",
    tags=["goalkeepers"],
    dependencies=[Depends(get_current_user)],
    responses=COMMON_ERROR_RESPONSES,
)


@router.post("", response_model=GoalkeeperResponse, status_code=status.HTTP_201_CREATED)
async def create_goalkeeper(
    gk_data: GoalkeeperCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(current_user) and gk_data.club_id != current_user.club_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    gk_repo = GoalkeeperRepository(db)
    return await gk_repo.create(
        club_id=gk_data.club_id,
        name=gk_data.name,
        birth_date=gk_data.birth_date,
        dominant_hand=gk_data.dominant_hand,
        height_cm=gk_data.height_cm,
        weight_kg=gk_data.weight_kg
    )


@router.get("", response_model=list[GoalkeeperResponse])
async def list_goalkeepers(
    club_id: UUID = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gk_repo = GoalkeeperRepository(db)
    scope = effective_club_scope(current_user)
    if scope is not None:
        # Nao-admin: sempre restrito ao proprio clube, independente do
        # club_id pedido na query.
        return await gk_repo.get_by_club_id(scope)
    if club_id:
        return await gk_repo.get_by_club_id(club_id)
    return await gk_repo.get_all()


@router.get("/{gk_id}", response_model=GoalkeeperResponse)
async def get_goalkeeper(
    gk_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gk_repo = GoalkeeperRepository(db)
    gk = await gk_repo.get_by_id(gk_id)
    if not gk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goalkeeper not found")
    if not is_admin(current_user) and gk.club_id != current_user.club_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return gk
