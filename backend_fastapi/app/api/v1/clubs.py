from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import ClubCreate, ClubResponse
from app.repositories.repositories import ClubRepository
from app.core.security import get_current_user
from app.core.authorization import require_roles, is_admin
from app.models.models import User, UserRole

router = APIRouter(prefix="/api/v1/clubs", tags=["clubs"], dependencies=[Depends(get_current_user)])


@router.post(
    "",
    response_model=ClubResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SYSTEM_ADMIN))],
)
async def create_club(club_data: ClubCreate, db: AsyncSession = Depends(get_db)):
    """Criar um novo clube (onboarding de um novo tenant). Restrito a SYSTEM_ADMIN."""
    club_repo = ClubRepository(db)
    return await club_repo.create(name=club_data.name, city=club_data.city)


@router.get("", response_model=list[ClubResponse])
async def list_clubs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    club_repo = ClubRepository(db)
    if is_admin(current_user):
        return await club_repo.get_all()
    own_club = await club_repo.get_by_id(current_user.club_id)
    return [own_club] if own_club else []


@router.get("/{club_id}", response_model=ClubResponse)
async def get_club(
    club_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    club_repo = ClubRepository(db)
    club = await club_repo.get_by_id(club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    if not is_admin(current_user) and current_user.club_id != club_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return club
