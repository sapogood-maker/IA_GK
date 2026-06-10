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
        
        # Temporary debug logs to inspect what password value is being passed
        try:
            print("DEBUG register - PASSWORD:", user_data.password)
            print("DEBUG register - TYPE:", type(user_data.password))
            try:
                print("DEBUG register - LEN:", len(user_data.password))
            except Exception:
                print("DEBUG register - LEN: n/a")
        except Exception as e:
            print("DEBUG register - Error printing password details:", e)
        
        # Normalize/validate password before hashing to avoid passing unexpected types
        password_raw = user_data.password
        if isinstance(password_raw, (bytes, bytearray)):
            try:
                password = password_raw.decode('utf-8')
            except Exception:
                password = str(password_raw)
        else:
            password = str(password_raw)

        # Ensure password fits bcrypt limit (72 bytes when UTF-8 encoded)
        password_bytes = password.encode('utf-8')
        print("DEBUG register - PASSWORD_ENCODED_LEN:", len(password_bytes))
        if len(password_bytes) > 72:
            raise ValueError("Password too long for bcrypt (max 72 bytes).")

        hashed_password = hash_password(password)
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
