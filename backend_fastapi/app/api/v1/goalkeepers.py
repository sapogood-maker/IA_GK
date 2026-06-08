from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import GoalkeeperCreate, GoalkeeperResponse
from app.repositories.repositories import GoalkeeperRepository

router = APIRouter(prefix="/api/v1/goalkeepers", tags=["goalkeepers"])


@router.post("", response_model=GoalkeeperResponse, status_code=status.HTTP_201_CREATED)
async def create_goalkeeper(gk_data: GoalkeeperCreate, db: AsyncSession = Depends(get_db)):
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
async def list_goalkeepers(club_id: UUID = None, db: AsyncSession = Depends(get_db)):
    gk_repo = GoalkeeperRepository(db)
    if club_id:
        return await gk_repo.get_by_club_id(club_id)
    return []


@router.get("/{gk_id}", response_model=GoalkeeperResponse)
async def get_goalkeeper(gk_id: UUID, db: AsyncSession = Depends(get_db)):
    gk_repo = GoalkeeperRepository(db)
    gk = await gk_repo.get_by_id(gk_id)
    if not gk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goalkeeper not found")
    return gk
