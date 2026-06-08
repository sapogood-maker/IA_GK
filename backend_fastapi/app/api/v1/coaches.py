from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import CoachCreate, CoachResponse
from app.repositories.repositories import CoachRepository

router = APIRouter(prefix="/api/v1/coaches", tags=["coaches"])


@router.post("", response_model=CoachResponse, status_code=status.HTTP_201_CREATED)
async def create_coach(coach_data: CoachCreate, db: AsyncSession = Depends(get_db)):
    coach_repo = CoachRepository(db)
    return await coach_repo.create(user_id=coach_data.user_id, club_id=coach_data.club_id)


@router.get("/{coach_id}", response_model=CoachResponse)
async def get_coach(coach_id: UUID, db: AsyncSession = Depends(get_db)):
    coach_repo = CoachRepository(db)
    coach = await coach_repo.get_by_id(coach_id)
    if not coach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
    return coach
