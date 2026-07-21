from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.base import get_db
from app.repositories.repositories import UserRepository

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema Bearer padrao do FastAPI: registra o security scheme no OpenAPI
# para que o Swagger exiba o cadeado e o botao "Authorize" funcione em
# todos os endpoints protegidos, sem exigir um header manual por rota.
# auto_error=False para preservar a mensagem/status originais (401) quando
# o header estiver ausente ou malformado, tratados explicitamente abaixo.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Informe o access_token obtido em POST /api/v1/auth/login",
)


class TokenData(BaseModel):
    user_id: str
    # Tokens de refresh carregam so o user_id (ver AuthService) - email/role
    # sao preenchidos apenas quando presentes no payload (tokens de acesso).
    email: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("user_id")

        # user_id e o unico claim obrigatorio em qualquer token (de acesso
        # ou de refresh). Exigir "email" aqui quebrava /auth/refresh, cujo
        # token so carrega user_id - achado real via testes automatizados
        # (ver SPRINT6_REPORT.md).
        if user_id is None:
            return None

        return TokenData(
            user_id=user_id,
            email=payload.get("email"),
            role=payload.get("role"),
        )
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Dependency to extract and validate JWT via the OAuth2/Bearer scheme."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    token_data = decode_token(credentials.credentials)

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
