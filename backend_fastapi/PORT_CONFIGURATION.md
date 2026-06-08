# Port Configuration - Goalkeeper AI Platform

## Reserved Ports

| Port | Service | Status | Description |
|------|---------|--------|-------------|
| **5432** | PostgreSQL Database | ✅ Active (Sprint 1) | Default PostgreSQL port |
| **8001** | FastAPI Backend | ✅ Active (Sprint 1) | REST API & OpenAPI docs |
| **8002** | AI Worker Service | 📝 Reserved (Sprint 2) | GPU-powered ML pipeline |

---

## Service Endpoints

### Development / Docker Compose

```bash
# PostgreSQL Database
postgresql://goalkeeper_user:goalkeeper_pass@localhost:5432/goalkeeper_ai

# FastAPI Backend (Sprint 1)
http://localhost:8001
http://localhost:8001/docs       (OpenAPI Swagger UI)
http://localhost:8001/health     (Health check)

# AI Worker (Sprint 2 - Reserved)
http://localhost:8002            (AI Worker API - Coming Soon)
```

### Local Development

```bash
# Backend server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# Access via
http://127.0.0.1:8001
http://127.0.0.1:8001/docs
```

---

## Configuration Files with Port References

### Updated Files (8000 → 8001)

1. **docker-compose.yml**
   - Backend service port mapping: `8001:8001`
   - AI Worker placeholder with port 8002 reserved

2. **README.md** (5 updates)
   - Quick start endpoint URLs
   - Example curl commands
   - API documentation links

3. **LOCAL_SETUP.md** (8 updates)
   - Server startup instructions
   - Health check endpoint
   - API testing examples

4. **00_START_HERE.md** (3 updates)
   - Docker Compose instructions
   - Production Docker example
   - Quick start guide

5. **STARTUP.md** (3 updates)
   - Quick start options
   - Example API calls
   - Health check

6. **QUICK_REFERENCE.md** (6 updates)
   - Command reference table
   - Sample API calls

7. **IMPLEMENTATION_COMPLETE.md** (4 updates)
   - Docker instructions
   - Quick start examples

8. **SPRINT_1_COMPLETE.md** (3 updates)
   - Docker and local dev setup
   - Test examples

9. **SPRINT_1_SUMMARY.txt** (3 updates)
   - Quick start section
   - API access examples

---

## Sprint Planning

### Sprint 1 ✅
```
Port 8001: FastAPI Backend
├─ Authentication (JWT)
├─ User Management (CRUD)
├─ Club Management (CRUD)
├─ Coach Management (CRUD)
└─ Goalkeeper Management (CRUD)
```

### Sprint 2 (Next - Port 8002 Reserved)
```
Port 8002: AI Worker Service (Coming Soon)
├─ Video processing pipeline
├─ Goalkeeper detection
├─ Event classification
└─ Model inference
```

### Communication Protocol
```
Client (Port 8001) 
    ↓
Backend (FastAPI, Port 8001)
    ↓
[REST API calls]
    ↓
AI Worker (Port 8002, Sprint 2)
```

---

## Network Architecture

```
┌─────────────────────────────────┐
│     Docker Compose Stack        │
├─────────────────────────────────┤
│                                 │
│  ┌────────────────────────────┐ │
│  │  PostgreSQL 5432           │ │
│  └────────────────────────────┘ │
│              ↑                  │
│              │                  │
│  ┌────────────────────────────┐ │
│  │ FastAPI Backend 8001       │ │
│  │ (app.main:app)             │ │
│  └────────────────────────────┘ │
│              ↑                  │
│    [REST API / JSON]            │
│              │                  │
│  ┌────────────────────────────┐ │
│  │ AI Worker 8002 (Reserved)  │ │
│  │ [Sprint 2]                 │ │
│  └────────────────────────────┘ │
│                                 │
└─────────────────────────────────┘
```

---

## How to Verify Ports

### Check Backend is Running
```bash
curl http://localhost:8001/health
# Response: {"status":"ok","service":"Goalkeeper AI API"}
```

### Check OpenAPI Available
```bash
curl http://localhost:8001/docs
# Should return Swagger UI HTML
```

### Check PostgreSQL is Running
```bash
psql postgresql://goalkeeper_user:goalkeeper_pass@localhost:5432/goalkeeper_ai
# Should connect to database
```

### List Active Ports (Linux/Mac)
```bash
lsof -i :8001
lsof -i :5432
```

### List Active Ports (Windows)
```powershell
netstat -ano | findstr :8001
netstat -ano | findstr :5432
```

### Check if Port is Available
```bash
# Before starting backend
python -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8001)); print('Port 8001 available')"
```

---

## Port Conflict Resolution

### If Port 8001 is Already in Use

**Option 1: Kill the existing process (Linux/Mac)**
```bash
# Find process
lsof -i :8001
# Kill it
kill -9 <PID>
```

**Option 2: Use a different port temporarily**
```bash
uvicorn app.main:app --reload --port 8003
# Access via http://localhost:8003
```

**Option 3: Find what's using the port (Windows)**
```powershell
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

---

## Docker Compose Port Mapping

```yaml
backend:
  ports:
    - "8001:8001"  # HOST:CONTAINER
  # Accessible via http://localhost:8001 from host

postgres:
  ports:
    - "5432:5432"  # HOST:CONTAINER
  # Accessible via localhost:5432 from host
```

---

## Production Deployment Notes

### Port 8001 (Backend)
- Use reverse proxy (Nginx/Traefik) on port 80/443
- Map internal 8001 to external 80/443
- Example: `nginx:80 → backend:8001`

### Port 8002 (AI Worker - Sprint 2)
- Dedicated GPU machine (internal network)
- Only accessible from backend via API key
- Not exposed to internet

### Port 5432 (PostgreSQL)
- DO NOT expose to internet
- Keep on private network only
- Backend connects via internal network

### Example Production Setup
```
Internet
  ↓
443 (HTTPS) ← Nginx/Traefik (Reverse Proxy)
  ↓
8001 (Backend API) ← Internal Docker network
  ↓
5432 (PostgreSQL) ← Private network only

[GPU Machine] ← AI Worker (8002, Private)
```

---

## Troubleshooting

### "Address already in use" error
**Cause**: Another service is using port 8001
**Solution**: 
- Change port temporarily: `--port 8003`
- Or kill existing process on port 8001

### "Cannot connect to backend" from Docker
**Cause**: Wrong hostname (using localhost instead of service name)
**Solution**:
- Inside Docker: Use `http://backend:8001` (not localhost)
- From host: Use `http://localhost:8001`

### "Port 5432 refused connection"
**Cause**: PostgreSQL container not running or not ready
**Solution**:
- Check: `docker compose ps`
- Restart: `docker compose restart postgres`
- Wait for health check (10s)

### "Database connection failed"
**Cause**: DATABASE_URL using wrong port
**Solution**:
- Check .env: Should use internal name in Docker
- `postgresql://goalkeeper_user:goalkeeper_pass@postgres:5432/goalkeeper_ai`

---

## Quick Reference

| Need | Command | Port |
|------|---------|------|
| Start backend | `uvicorn app.main:app --reload --port 8001` | 8001 |
| Docker Compose | `docker compose up` | 8001, 5432 |
| API Docs | Visit `http://localhost:8001/docs` | 8001 |
| Health Check | `curl http://localhost:8001/health` | 8001 |
| Database | `psql ... localhost:5432` | 5432 |

---

**Last Updated**: 2026-06-08
**Version**: Sprint 1 (Port 8001 Active, Port 8002 Reserved)
