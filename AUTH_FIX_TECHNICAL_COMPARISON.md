# Comparação Técnica: Antes vs Depois

## Arquivo: `backend_fastapi/app/api/v1/auth.py`

### CÓDIGO ANTERIOR (Problema)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.schemas.schemas import UserCreate, TokenResponse, LoginRequest, TokenRefresh
from app.services.auth_service import AuthService
from app.core.security import decode_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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


# ❌ PROBLEMA: authorization é query parameter com default None
@router.get("/me")
async def get_current_user(authorization: str = None, db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    
    token = authorization.split(" ")[1]
    token_data = decode_token(token)
    
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    from app.repositories.repositories import UserRepository
    user_repo = UserRepository(db)
    from uuid import UUID
    user = await user_repo.get_by_id(UUID(token_data.user_id))
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role
    }
```

---

### CÓDIGO NOVO (Corrigido)

```python
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.schemas.schemas import UserCreate, TokenResponse, LoginRequest, TokenRefresh
from app.services.auth_service import AuthService
from app.core.security import decode_token
from uuid import UUID
from app.repositories.repositories import UserRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ✅ NOVO: Dependência centralizada de autenticação
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


# ✅ CORRIGIDO: Usa dependência centralizada
@router.get("/me")
async def me(user = Depends(get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role
    }
```

---

## Tabela Comparativa

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Parâmetro authorization** | `str = None` | `str = Header(...)` |
| **Tipo de entrada** | Query Parameter | HTTP Header |
| **Obrigatoriedade** | Opcional (None como default) | Obrigatório (`...`) |
| **Imports** | ❌ Sem `Header` | ✅ Com `Header` |
| **Função do endpoint** | Faz validação + busca | Apenas retorna dados |
| **Código no endpoint** | 19 linhas | 6 linhas |
| **Reutilização** | ❌ Duplicado | ✅ Centralizado em `get_current_user` |
| **Swagger** | Query param (`?authorization=`) | Header com lock icon |
| **Segurança** | ⚠️ Exposto em logs | ✅ Em header (RFC 7235) |
| **Erro de header ausente** | "Missing token" | "Missing or invalid authorization header" |

---

## Mudanças Linha por Linha

### Imports

```diff
  from fastapi import APIRouter, Depends, HTTPException, status
+ from fastapi import Header
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.db.base import get_db
  from app.schemas.schemas import UserCreate, TokenResponse, LoginRequest, TokenRefresh
  from app.services.auth_service import AuthService
  from app.core.security import decode_token
+ from uuid import UUID
+ from app.repositories.repositories import UserRepository
- (imports removidos de dentro da função)
```

### Função de Dependência

```diff
- (Não existia antes)
+ async def get_current_user(authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
+     """Dependency to extract and validate JWT from Authorization header."""
+     if not authorization or not authorization.startswith("Bearer "):
+         raise HTTPException(
+             status_code=status.HTTP_401_UNAUTHORIZED,
+             detail="Missing or invalid authorization header"
+         )
+     
+     token = authorization.split(" ")[1]
+     token_data = decode_token(token)
+     
+     if not token_data:
+         raise HTTPException(
+             status_code=status.HTTP_401_UNAUTHORIZED,
+             detail="Invalid token"
+         )
+     
+     user_repo = UserRepository(db)
+     user = await user_repo.get_by_id(UUID(token_data.user_id))
+     
+     if not user:
+         raise HTTPException(
+             status_code=status.HTTP_404_NOT_FOUND,
+             detail="User not found"
+         )
+     
+     return user
```

### Endpoint `/me`

```diff
  @router.get("/me")
- async def get_current_user(authorization: str = None, db: AsyncSession = Depends(get_db)):
-     if not authorization or not authorization.startswith("Bearer "):
-         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
-     
-     token = authorization.split(" ")[1]
-     token_data = decode_token(token)
-     
-     if not token_data:
-         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
-     
-     from app.repositories.repositories import UserRepository
-     user_repo = UserRepository(db)
-     from uuid import UUID
-     user = await user_repo.get_by_id(UUID(token_data.user_id))
-     
-     if not user:
-         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
-     
+ async def me(user = Depends(get_current_user)):
+     """Get current authenticated user information."""
      return {
          "id": str(user.id),
          "name": user.name,
          "email": user.email,
          "role": user.role
      }
```

---

## Teste de Request/Response

### Antes (Query Parameter - ❌)

```http
GET /api/v1/auth/me?authorization=Bearer%20eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Depois (Header - ✅)

```http
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Documentação no Swagger

### Antes
![Swagger Before]
- Mostra `authorization` como query parameter
- Sem indicação de autenticação
- Documentação confusa

### Depois
![Swagger After]
- Mostra `Authorization` como header obrigatório
- Lock icon indica autenticação
- Swagger auto-gera corretamente

---

## Teste de Compatibilidade

### Flutter (Sem mudanças necessárias)

```dart
// Código Flutter continua igual ✅
final response = await http.get(
  Uri.parse('$baseUrl/auth/me'),
  headers: {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  },
);
```

### cURL

```bash
# Teste o endpoint
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### JavaScript/Fetch

```javascript
// Código JavaScript continua igual ✅
fetch('/api/v1/auth/me', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
```

---

## Validação de Fluxo Completo

```
1. POST /api/v1/auth/login
   Request:  { email, password }
   Response: { access_token, refresh_token }
   
2. GET /api/v1/auth/me
   Request:  Authorization: Bearer {access_token}
   Response: { id, name, email, role }  ✅ AGORA CORRETO
   
3. POST /api/v1/auth/refresh
   Request:  { refresh_token }
   Response: { access_token, refresh_token }
```

---

*Documento técnico de mudanças*  
*Data: 2026-06-10*  
*Status: ✅ Implementado*
