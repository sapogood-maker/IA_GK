# Sprint 1 - Local Setup & Testing Guide

## Local Development Setup (Without Docker)

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ running locally or accessible
- pip

### Step 1: Setup Virtual Environment

```bash
cd backend_fastapi

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy example env
cp .env.example .env

# Edit .env with your PostgreSQL credentials
# Example for local PostgreSQL:
# DATABASE_URL=postgresql://username:password@localhost:5432/goalkeeper_ai
```

### Step 4: Database Setup

```bash
# Create the database in PostgreSQL first:
createdb goalkeeper_ai -U <your_postgres_user>

# Or using psql:
# psql -U postgres
# CREATE DATABASE goalkeeper_ai;
# \q
```

### Step 5: Run the Application

```bash
# Start the FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

The server will start at `http://127.0.0.1:8001`

### Step 6: Test the API

Open browser or use curl:

**Health Check:**
```bash
curl http://127.0.0.1:8001/health
```

**OpenAPI Documentation (Interactive):**
```
http://127.0.0.1:8001/docs
```

**Register a User:**
```bash
curl -X POST http://127.0.0.1:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Coach João",
    "email": "joao@example.com",
    "password": "MySecurePass123!",
    "role": "coach"
  }'
```

Expected Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Login:**
```bash
curl -X POST http://127.0.0.1:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "joao@example.com",
    "password": "MySecurePass123!"
  }'
```

**Get Current User (use token from login response):**
```bash
curl -X GET http://127.0.0.1:8001/api/v1/auth/me \
  -H "Authorization: Bearer <your_access_token>"
```

**Create a Club:**
```bash
curl -X POST http://127.0.0.1:8001/api/v1/clubs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FC Futsal São Paulo",
    "city": "São Paulo"
  }'
```

Expected Response (note the club_id):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "FC Futsal São Paulo",
  "city": "São Paulo",
  "created_at": "2026-06-08T15:15:30.123456+00:00"
}
```

**Create a Goalkeeper:**
```bash
curl -X POST http://127.0.0.1:8001/api/v1/goalkeepers \
  -H "Content-Type: application/json" \
  -d '{
    "club_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "João Silva",
    "birth_date": "1995-06-15T00:00:00Z",
    "dominant_hand": "right",
    "height_cm": 185,
    "weight_kg": 82
  }'
```

**List Goalkeepers by Club:**
```bash
curl -X GET "http://127.0.0.1:8001/api/v1/goalkeepers?club_id=550e8400-e29b-41d4-a716-446655440000"
```

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not connect to server: Connection refused
```
- Verify PostgreSQL is running: `psql -U postgres -c "SELECT 1"`
- Check DATABASE_URL in .env is correct
- Verify database exists: `psql -U postgres -l | grep goalkeeper_ai`

### Module Import Errors
```
ModuleNotFoundError: No module named 'app'
```
- Make sure you're running from `backend_fastapi` directory
- Verify virtual environment is activated
- Reinstall packages: `pip install -r requirements.txt`

### Port Already in Use
```
Address already in use
```
- Change port: `uvicorn app.main:app --port 8002`
- Or find and kill process on port 8001

### JWT Token Expired
- Tokens expire after `JWT_EXPIRATION_MINUTES` (default 30 minutes)
- Use refresh endpoint to get new access token

## Testing with Postman/Insomnia

1. Create a new collection
2. Import OpenAPI schema from `http://localhost:8001/openapi.json`
3. All endpoints will be pre-configured
4. Set environment variables for `BASE_URL` and `TOKEN`

## Code Quality

### Format Code
```bash
# Install formatter (optional)
pip install black

# Format all Python files
black app/
```

### Check Types (Optional)
```bash
# Install type checker
pip install mypy

# Check types
mypy app/
```

## Next Steps

- Sprint 2: Video upload, processing jobs, WebSocket updates
- Sprint 3: Goalkeeper detection, event classification, reports
- Sprint 4: AI Assistant and RAG integration

## Production Deployment Notes

When deploying to production:
1. Change `JWT_SECRET_KEY` to a strong random value
2. Use strong PostgreSQL credentials
3. Set `ENV=production`
4. Use environment variables for all sensitive data
5. Set up HTTPS/SSL
6. Configure CORS properly (not "*")
7. Add rate limiting
8. Set up monitoring and logging
9. Use connection pooling for database
10. Implement automated backups

See deployment documentation when ready for production deployment.
