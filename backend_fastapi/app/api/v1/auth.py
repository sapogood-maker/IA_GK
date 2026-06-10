from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.schemas.schemas import UserCreate, TokenResponse, LoginRequest, TokenRefresh
from app.services.auth_service import AuthService
from app.core.security import decode_token
from uuid import UUID
from app.repositories.repositories import UserRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def get_current_user(authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
    """Dependency to extract and validate JWT from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    token_data = decode_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(token_data.user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.register(user_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.login(credentials.email, credentials.password)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.refresh_access_token(data.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")


@router.get("/me")
async def me(user = Depends(get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role
    }
