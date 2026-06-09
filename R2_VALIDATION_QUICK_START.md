# R2 Validation - Quick Start

## What Was Implemented

### ✅ Two REST Endpoints

**1. GET /api/v1/r2/health**
```bash
curl http://localhost:8001/api/v1/r2/health
```
Returns: `{ "status": "ok", "bucket": "name", "read_access": true, "write_access": true }`

**2. POST /api/v1/r2/test-upload**
```bash
curl -X POST http://localhost:8001/api/v1/r2/test-upload
```
Returns: `{ "status": "success", "message": "R2 write access verified successfully" }`

---

## Setup (3 Steps)

### 1. Configure .env
```env
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name
```

### 2. Start Server
```bash
cd backend_fastapi
python -m uvicorn app.main:app --reload --port 8001
```

### 3. Test
```bash
curl http://localhost:8001/api/v1/r2/health | jq
```

---

## What It Validates

✓ All 4 required environment variables are set  
✓ R2 bucket exists and is accessible  
✓ Read permission (can list objects)  
✓ Write permission (can upload/delete files)  

---

## Error Handling

| Issue | Error Message | Solution |
|-------|---------------|----------|
| Missing env vars | `Missing required environment variables: ...` | Add to .env |
| Wrong bucket | `Bucket 'name' does not exist` | Check bucket name |
| No permissions | `No access to bucket 'name'. Check permissions.` | Update API token |
| Read permission | `Read access check failed: AccessDenied` | Add Object Read permission |
| Write permission | `Write access check failed: AccessDenied` | Add Object Write permission |

See `docs/R2_VALIDATION.md` for detailed troubleshooting.

---

## Files Created/Modified

**Created:**
- `backend_fastapi/app/api/v1/r2.py` - Endpoints
- `docs/R2_VALIDATION.md` - Full documentation

**Enhanced:**
- `backend_fastapi/app/core/r2.py` - Better error handling + validation methods
- `backend_fastapi/app/main.py` - R2 route + startup validation
- `backend_fastapi/app/core/config.py` - Field validators

---

## Key Features

✅ Immediate verification after .env setup  
✅ Comprehensive error messages  
✅ Automatic test file cleanup  
✅ Non-blocking startup validation  
✅ Production-ready error handling  
✅ Full documentation with examples  

---

For detailed setup and troubleshooting, see: `docs/R2_VALIDATION.md`
