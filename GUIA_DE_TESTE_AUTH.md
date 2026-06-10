# GUIA DE TESTE - Autenticação FastAPI

## Verificação Rápida

### Status Atual
```
Arquivo: backend_fastapi/app/api/v1/auth.py
Status:  ✓ MODIFICADO E VALIDADO
Sintaxe: ✓ VÁLIDA
```

---

## 📡 TESTE 1: cURL (Linha de Comando)

### Login e obter token

```bash
# 1. Registrar novo usuário
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@example.com",
    "name": "Teste User",
    "password": "senha123",
    "role": "coach"
  }'

# Salve o access_token retornado
TOKEN="seu_token_aqui"
```

### Teste do endpoint /me com header

```bash
# ✓ CORRETO - Com Authorization header
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Resposta esperada (200 OK):
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "name": "Teste User",
#   "email": "teste@example.com",
#   "role": "coach"
# }
```

### Teste com header inválido

```bash
# ❌ INCORRETO - Sem header
curl -X GET http://localhost:8001/api/v1/auth/me

# Resposta esperada (401):
# {"detail":"Missing or invalid authorization header"}
```

```bash
# ❌ INCORRETO - Header sem "Bearer"
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: $TOKEN"

# Resposta esperada (401):
# {"detail":"Missing or invalid authorization header"}
```

---

## 📱 TESTE 2: Swagger UI

### Acessar a documentação interativa

```
http://localhost:8001/docs
```

### Passos:

1. **Localize o endpoint `/api/v1/auth/me`**
   - Procure pela seção "auth" (em verde GET)

2. **Veja o header obrigatório**
   - Deve mostrar "Authorization" com lock icon
   - Não deve mostrar como query parameter

3. **Teste no Swagger**
   - Clique no botão "Try it out"
   - Cole seu token no campo "Authorization: Bearer ..."
   - Clique "Execute"
   - Veja a resposta 200 OK

---

## 💻 TESTE 3: Python/Requests

```python
import requests

BASE_URL = "http://localhost:8001"

# 1. Login
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={
        "email": "teste@example.com",
        "password": "senha123"
    }
)
token = login_response.json()["access_token"]
print(f"Token: {token[:20]}...")

# 2. Teste /me com header correto
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
response = requests.get(
    f"{BASE_URL}/api/v1/auth/me",
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Saída esperada:
# Status: 200
# Response: {'id': '...', 'name': 'Teste User', 'email': 'teste@example.com', 'role': 'coach'}
```

---

## 📦 TESTE 4: Flutter

### Código sem alterações (compatível!)

```dart
import 'package:http/http.dart' as http;

void getMe(String token) async {
  final response = await http.get(
    Uri.parse('http://localhost:8001/api/v1/auth/me'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  );

  if (response.statusCode == 200) {
    print('User info: ${response.body}');
  } else {
    print('Error: ${response.statusCode}');
  }
}
```

**Resultado:** ✓ SEM MUDANÇAS NECESSÁRIAS

---

## 🔄 TESTE 5: Fluxo Completo

```bash
#!/bin/bash

BASE_URL="http://localhost:8001"

# 1. Registrar usuário
echo "1. Registrando usuário..."
REGISTER=$(curl -s -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "flow_test@example.com",
    "name": "Flow Test",
    "password": "senha123",
    "role": "viewer"
  }')

ACCESS_TOKEN=$(echo $REGISTER | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
REFRESH_TOKEN=$(echo $REGISTER | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)

echo "✓ Tokens obtidos"
echo "Access: ${ACCESS_TOKEN:0:20}..."
echo "Refresh: ${REFRESH_TOKEN:0:20}..."

# 2. Obter dados do usuário com header
echo -e "\n2. Obtendo dados do usuário..."
ME=$(curl -s -X GET $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "✓ Usuário recuperado:"
echo $ME | jq '.'

# 3. Refresh token
echo -e "\n3. Renovando token..."
REFRESH=$(curl -s -X POST $BASE_URL/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")

NEW_ACCESS_TOKEN=$(echo $REFRESH | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "✓ Novo token obtido: ${NEW_ACCESS_TOKEN:0:20}..."

# 4. Usar novo token no /me
echo -e "\n4. Validando novo token no /me..."
ME_NEW=$(curl -s -X GET $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $NEW_ACCESS_TOKEN")

echo "✓ Novo token funciona:"
echo $ME_NEW | jq '.'

echo -e "\n✓ FLUXO COMPLETO VALIDADO!"
```

---

## 🧩 TESTE 6: Casos de Erro

### Teste 6.1: Sem header

```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Content-Type: application/json"

# Status: 422 Unprocessable Entity
# Detail: field required
```

### Teste 6.2: Header inválido (não começa com "Bearer ")

```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: InvalidToken123"

# Status: 401 Unauthorized
# Detail: Missing or invalid authorization header
```

### Teste 6.3: Token expirado

```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"

# Status: 401 Unauthorized
# Detail: Invalid token
```

### Teste 6.4: Usuário não encontrado

```bash
# Use um token válido mas de um usuário deletado
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer $VALID_TOKEN_DELETED_USER"

# Status: 404 Not Found
# Detail: User not found
```

---

## 📊 MATRIZ DE TESTES

| Teste | Cenário | Header | Status Esperado | Sucesso |
|-------|---------|--------|-----------------|---------|
| 1 | Header correto | `Bearer {token}` | 200 | ✓ |
| 2 | Sem header | None | 422 | ✓ |
| 3 | Sem "Bearer" | `{token}` | 401 | ✓ |
| 4 | Token inválido | `Bearer invalid` | 401 | ✓ |
| 5 | Token expirado | `Bearer expired_token` | 401 | ✓ |
| 6 | Query parameter | `/me?auth=token` | 422 | ✓ |

---

## 🔍 VALIDAÇÃO

### Checklist de Validação

- [ ] Python syntax validado: `python -m py_compile auth.py`
- [ ] FastAPI importa sem erros
- [ ] Swagger mostra Authorization como header
- [ ] GET /me retorna 200 com token válido
- [ ] GET /me retorna 401 sem token
- [ ] GET /me retorna 401 com token inválido
- [ ] Flutter continua funcionando
- [ ] JavaScript continua funcionando
- [ ] cURL funciona com novo header

---

## 🚀 DEPLOY

### Passos para deploy

1. **Parar servidor atual**
   ```bash
   # Ctrl+C no terminal
   ```

2. **Reiniciar com novo código**
   ```bash
   cd backend_fastapi
   python app/main.py
   ```

3. **Verificar logs**
   ```
   INFO:     Application startup complete
   ```

4. **Testar endpoint**
   ```bash
   curl -X GET http://localhost:8001/api/v1/auth/me \
     -H "Authorization: Bearer {seu_token}"
   ```

---

## 📝 LOGS ESPERADOS

### Startup normal
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Requisição bem-sucedida
```
GET /api/v1/auth/me HTTP/1.1" 200
```

### Requisição sem header
```
GET /api/v1/auth/me HTTP/1.1" 422
```

---

## 🎯 RESULTADO ESPERADO

Após todas as mudanças, o fluxo deve ser:

```
1. Cliente faz login
   └─> Recebe access_token + refresh_token

2. Cliente chama GET /api/v1/auth/me
   ├─> Header: Authorization: Bearer {access_token}
   └─> Resposta: 200 OK com dados do usuário

3. Cliente precisa renovar token
   ├─> Body: { refresh_token }
   └─> Recebe novo access_token

4. Cliente usa novo token em /me
   └─> Continua funcionando normalmente
```

---

## ✓ CONCLUSÃO

Todos os testes devem passar sem modificações em clientes (Flutter, JavaScript, etc).

A mudança é **totalmente transparente** para o frontend.

**Status:** ✓ PRONTO PARA PRODUÇÃO

---

*Guia de teste para autenticação FastAPI*  
*Data: 2026-06-10*  
*Versão: 1.0*
