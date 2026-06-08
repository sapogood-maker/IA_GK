from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import TrainingSessionCreate, TrainingSessionResponse, TrainingSessionUpdate
from app.repositories.repositories import TrainingSessionRepository, GoalkeeperRepository, CoachRepository

router = APIRouter(prefix="/api/v1/training-sessions", tags=["training-sessions"])


@router.post("", response_model=TrainingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_training_session(session_data: TrainingSessionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new training session."""
    gk_repo = GoalkeeperRepository(db)
    coach_repo = CoachRepository(db)
    
    # Validate goalkeeper exists
    gk = await gk_repo.get_by_id(session_data.goalkeeper_id)
    if not gk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goalkeeper not found")
    
    # Validate coach exists if provided
    if session_data.coach_id:
        coach = await coach_repo.get_by_id(session_data.coach_id)
        if not coach:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
    
    session_repo = TrainingSessionRepository(db)
    return await session_repo.create(
        goalkeeper_id=session_data.goalkeeper_id,
        coach_id=session_data.coach_id,
        title=session_data.title,
        session_type=session_data.session_type,
        session_date=session_data.session_date,
        notes=session_data.notes
    )


@router.get("", response_model=list[TrainingSessionResponse])
async def list_training_sessions(
    goalkeeper_id: UUID = None,
    coach_id: UUID = None,
    db: AsyncSession = Depends(get_db)
):
    """List training sessions with optional filtering."""
    session_repo = TrainingSessionRepository(db)
    
    if goalkeeper_id:
        return await session_repo.get_by_goalkeeper_id(goalkeeper_id)
    elif coach_id:
        return await session_repo.get_by_coach_id(coach_id)
    else:
        return await session_repo.get_all()


@router.get("/{session_id}", response_model=TrainingSessionResponse)
async def get_training_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific training session."""
    session_repo = TrainingSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
    return session


@router.put("/{session_id}", response_model=TrainingSessionResponse)
async def update_training_session(
    session_id: UUID,
    session_data: TrainingSessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a training session."""
    session_repo = TrainingSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
    
    update_data = session_data.model_dump(exclude_unset=True)
    return await session_repo.update(session_id, **update_data)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a training session."""
    session_repo = TrainingSessionRepository(db)
    success = await session_repo.delete(session_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
