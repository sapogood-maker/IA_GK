from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import timedelta
from app.repositories.repositories import UserRepository, ClubRepository, CoachRepository, GoalkeeperRepository
from app.core.security import hash_password, verify_password, create_token, decode_token
from app.schemas.schemas import UserCreate, TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, user_data: UserCreate) -> TokenResponse:
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("User already exists")
        
        hashed_password = hash_password(user_data.password)
        user = await self.user_repo.create(
            email=user_data.email,
            name=user_data.name,
            password_hash=hashed_password,
            role=user_data.role
        )
        
        access_token = create_token({
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role
        })
        
        refresh_token = create_token(
            {"user_id": str(user.id)},
            expires_delta=timedelta(days=7)
        )
        
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        
        access_token = create_token({
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role
        })
        
        refresh_token = create_token(
            {"user_id": str(user.id)},
            expires_delta=timedelta(days=7)
        )
        
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        token_data = decode_token(refresh_token)
        if not token_data:
            raise ValueError("Invalid refresh token")
        
        user = await self.user_repo.get_by_id(UUID(token_data.user_id))
        if not user:
            raise ValueError("User not found")
        
        access_token = create_token({
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role
        })
        
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
