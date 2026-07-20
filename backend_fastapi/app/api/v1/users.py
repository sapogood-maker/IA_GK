from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import UserResponse
from app.repositories.repositories import UserRepository
from app.core.security import get_current_user
from app.core.authorization import require_roles, is_admin
from app.models.models import User, UserRole

router = APIRouter(prefix="/api/v1/users", tags=["users"], dependencies=[Depends(get_current_user)])


@router.get(
    "",
    response_model=list[UserResponse],
    dependencies=[Depends(require_roles(UserRole.SYSTEM_ADMIN))],
)
async def list_users(db: AsyncSession = Depends(get_db)):
    """Lista todos os usuarios do sistema. Restrito a SYSTEM_ADMIN."""
    user_repo = UserRepository(db)
    return await user_repo.get_all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Um usuario so pode ver o proprio registro; SYSTEM_ADMIN ve qualquer um."""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
