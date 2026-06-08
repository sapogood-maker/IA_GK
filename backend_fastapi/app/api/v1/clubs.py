from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import ClubCreate, ClubResponse
from app.repositories.repositories import ClubRepository

router = APIRouter(prefix="/api/v1/clubs", tags=["clubs"])


@router.post("", response_model=ClubResponse, status_code=status.HTTP_201_CREATED)
async def create_club(club_data: ClubCreate, db: AsyncSession = Depends(get_db)):
    club_repo = ClubRepository(db)
    return await club_repo.create(name=club_data.name, city=club_data.city)


@router.get("", response_model=list[ClubResponse])
async def list_clubs(db: AsyncSession = Depends(get_db)):
    club_repo = ClubRepository(db)
    return await club_repo.get_all()


@router.get("/{club_id}", response_model=ClubResponse)
async def get_club(club_id: UUID, db: AsyncSession = Depends(get_db)):
    club_repo = ClubRepository(db)
    club = await club_repo.get_by_id(club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    return club
