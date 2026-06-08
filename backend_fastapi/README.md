# Sprint 1 - FastAPI Backend Implementation

## Folder Structure

```
backend_fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Settings from .env
│   │   └── security.py         # JWT + password hashing
│   ├── db/
│   │   ├── __init__.py
│   │   └── base.py             # SQLAlchemy engine & session
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py           # SQLAlchemy ORM models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── repositories.py     # Data access layer
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py     # Business logic
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── auth.py         # Authentication endpoints
│           ├── users.py        # User endpoints
│           ├── clubs.py        # Club endpoints
│           ├── coaches.py      # Coach endpoints
│           └── goalkeepers.py  # Goalkeeper endpoints
│
├── alembic/
│   ├── __init__.py
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
│
├── tests/
│   └── __init__.py
│
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Local dev environment
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── alembic.ini             # Alembic config
├── API_ENDPOINTS.md        # Full API documentation
└── README.md               # This file
```

## Database Schema Overview

### Users Table
- id (UUID, PK)
- name (String)
- email (String, unique)
- password_hash (String)
- role (String: admin, club_admin, coach, viewer)
- created_at (DateTime)
- updated_at (DateTime)

### Clubs Table
- id (UUID, PK)
- name (String)
- city (String, optional)
- created_at (DateTime)

### Coaches Table
- id (UUID, PK)
- user_id (UUID, FK → Users)
- club_id (UUID, FK → Clubs, optional)
- created_at (DateTime)

### Goalkeepers Table
- id (UUID, PK)
- club_id (UUID, FK → Clubs)
- name (String)
- birth_date (DateTime, optional)
- dominant_hand (String, optional)
- height_cm (String, optional)
- weight_kg (String, optional)
- created_at (DateTime)

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for local development)

### Option 1: Docker Compose (Recommended for Development)

1. **Clone and navigate to backend directory:**
   ```bash
   cd backend_fastapi
   ```

2. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Start services:**
   ```bash
   docker-compose up
   ```

4. **API is running at:**
   - `http://localhost:8001`
   - OpenAPI docs: `http://localhost:8001/docs`
   - Health check: `http://localhost:8001/health`

### Option 2: Local Development

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up .env file:**
   ```bash
   cp .env.example .env
   # Edit .env and set DATABASE_URL to your PostgreSQL connection
   ```

4. **Run migrations (optional with Alembic):**
   ```bash
   alembic upgrade head
   ```

5. **Start the server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

## Testing the API

### Register a new user
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Coach",
    "email": "coach@example.com",
    "password": "securepass123",
    "role": "coach"
  }'
```

### Login
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "coach@example.com",
    "password": "securepass123"
  }'
```

### Create a club
```bash
curl -X POST http://localhost:8001/api/v1/clubs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FC Futsal Club",
    "city": "São Paulo"
  }'
```

### Create a goalkeeper
```bash
curl -X POST http://localhost:8001/api/v1/goalkeepers \
  -H "Content-Type: application/json" \
  -d '{
    "club_id": "00000000-0000-0000-0000-000000000000",
    "name": "João Silva",
    "birth_date": "1995-06-15T00:00:00Z",
    "dominant_hand": "right",
    "height_cm": 185,
    "weight_kg": 82
  }'
```

## API Documentation

See `API_ENDPOINTS.md` for complete endpoint list with request/response examples.

## Key Features - Sprint 1

✅ User authentication (register, login, refresh token, current user)
✅ User management (CRUD)
✅ Club management (CRUD)
✅ Coach management (CRUD)
✅ Goalkeeper management (CRUD)
✅ JWT-based authentication
✅ SQLAlchemy ORM models
✅ PostgreSQL database with migrations
✅ OpenAPI documentation
✅ Docker and Docker Compose support
✅ Health check endpoint
✅ Repository pattern for data access
✅ Service layer for business logic

## Next Steps (Sprint 2)

- [ ] Video upload endpoints with pre-signed R2 URLs
- [ ] Processing job management
- [ ] Training session management
- [ ] WebSocket for real-time updates
- [ ] Advanced filtering and pagination
- [ ] Unit and integration tests

## Environment Variables

See `.env.example` for all available options:
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Secret key for token signing
- `JWT_ALGORITHM`: Algorithm for JWT (default: HS256)
- `JWT_EXPIRATION_MINUTES`: Access token expiration (default: 30)
- `REFRESH_TOKEN_EXPIRATION_DAYS`: Refresh token expiration (default: 7)
- `ENV`: Environment (development or production)

## Database Connection Notes

PostgreSQL is required. By default with docker-compose:
- Host: `postgres` (inside container) or `localhost` (from host)
- Port: `5432`
- User: `goalkeeper_user`
- Password: `goalkeeper_pass`
- Database: `goalkeeper_ai`

For production, use strong credentials and secure PostgreSQL instance.
