# R2 Validation Guide

## Overview

The R2 Validation system provides endpoints to verify that Cloudflare R2 storage is properly configured and accessible. After configuring your `.env` file with R2 credentials, you can immediately test R2 connectivity and access permissions.

## Required Environment Variables

To use R2 features, configure these required variables in your `.env` file:

```env
R2_ACCOUNT_ID=<your-cloudflare-account-id>
R2_ACCESS_KEY_ID=<your-access-key-id>
R2_SECRET_ACCESS_KEY=<your-secret-access-key>
R2_BUCKET_NAME=<your-bucket-name>
R2_PUBLIC_URL=<optional-custom-domain>
```

### Getting Your Credentials

1. **R2_ACCOUNT_ID**: Found in Cloudflare dashboard → R2 → Account ID (looks like: `a1b2c3d4e5f6g7h8`)
2. **R2_ACCESS_KEY_ID** & **R2_SECRET_ACCESS_KEY**: Create in Cloudflare dashboard → R2 → API Tokens → Create API Token
   - Permissions: `Object Read`, `Object Write`, `Bucket Read`
3. **R2_BUCKET_NAME**: The name of your R2 bucket
4. **R2_PUBLIC_URL** (optional): Custom domain if you have one configured for your R2 bucket

## Endpoints

### GET `/api/v1/r2/health`

Comprehensive health check for R2 integration.

**What it checks:**
- ✓ Authentication credentials are configured
- ✓ R2 bucket exists and is accessible
- ✓ Read access to bucket (list objects)
- ✓ Write access to bucket (creates and deletes test file)

**Request:**
```bash
curl -X GET http://localhost:8001/api/v1/r2/health
```

**Success Response (200 OK):**
```json
{
  "status": "ok",
  "bucket": "my-bucket",
  "read_access": true,
  "write_access": true
}
```

**Error Response (503 Service Unavailable):**
```json
{
  "detail": "Missing required environment variables: R2_ACCOUNT_ID, R2_SECRET_ACCESS_KEY"
}
```

**Common Errors:**
- `Missing required environment variables: ...` - Check that all four required env vars are set
- `Bucket 'my-bucket' does not exist` - Verify bucket name is correct and exists in R2
- `No access to bucket 'my-bucket'. Check permissions.` - Verify API token has Object Read/Write permissions
- `Read access check failed: AccessDenied` - API token is missing List Objects permission
- `Write access check failed: AccessDenied` - API token is missing Object Write permission

---

### POST `/api/v1/r2/test-upload`

Test write access by uploading a test file, verifying it exists, and deleting it.

**What it does:**
1. Creates a temporary test file locally
2. Uploads it to R2 (`.validation/test-upload.tmp`)
3. Verifies the file exists in R2
4. Deletes the file from R2
5. Verifies deletion was successful
6. Cleans up temporary local file

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/r2/test-upload
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "R2 write access verified successfully"
}
```

**Error Response (503 Service Unavailable):**
```json
{
  "detail": "Test upload failed: Failed to upload test file"
}
```

**Common Errors:**
- `Missing required environment variables: ...` - Check `.env` configuration
- `Bucket 'my-bucket' does not exist` - Verify bucket exists
- `No access to bucket 'my-bucket'. Check permissions.` - Check API permissions
- `Failed to upload test file` - Write permission missing or quota exceeded
- `Test upload failed: Test file not found after upload` - Upload succeeded but file not immediately visible
- `Test upload failed: Test file still exists after deletion` - Delete operation failed or permission issue

---

## Usage Workflow

### 1. Configure Environment Variables

Create or update `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/goalkeeper_ai
JWT_SECRET_KEY=your-secret-key-here

# R2 Configuration
R2_ACCOUNT_ID=a1b2c3d4e5f6g7h8
R2_ACCESS_KEY_ID=abc123def456
R2_SECRET_ACCESS_KEY=xyz789uvw012
R2_BUCKET_NAME=goalkeeper-videos
```

### 2. Start the API Server

```bash
cd backend_fastapi
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

You should see in logs:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
INFO:     R2 configuration validated. R2 features are available.
```

### 3. Check Health Status

```bash
curl -X GET http://localhost:8001/api/v1/r2/health | jq
```

Expected output:
```json
{
  "status": "ok",
  "bucket": "goalkeeper-videos",
  "read_access": true,
  "write_access": true
}
```

### 4. Test Write Access

```bash
curl -X POST http://localhost:8001/api/v1/r2/test-upload | jq
```

Expected output:
```json
{
  "status": "success",
  "message": "R2 write access verified successfully"
}
```

### 5. Verify in R2 Dashboard (Optional)

You can verify the bucket in the Cloudflare R2 dashboard:
- Navigate to R2 → Your Bucket
- You should see a `.validation` folder with temporary test files (cleaned up automatically)

---

## Troubleshooting

### Issue: "Missing required environment variables"

**Solution:** Verify all four required environment variables are set in `.env`:
```bash
# On Unix/Linux/Mac:
grep -E "R2_ACCOUNT_ID|R2_ACCESS_KEY_ID|R2_SECRET_ACCESS_KEY|R2_BUCKET_NAME" .env

# On Windows PowerShell:
Select-String -Path .env -Pattern "R2_"
```

Each should have a non-empty value.

---

### Issue: "Bucket does not exist"

**Solution:** Check the bucket name:
1. Open Cloudflare Dashboard → R2
2. Verify the exact bucket name (case-sensitive)
3. Update `R2_BUCKET_NAME` in `.env` to match exactly
4. Restart the application

---

### Issue: "No access to bucket. Check permissions."

**Solution:** Verify API token permissions:
1. Go to Cloudflare Dashboard → R2 → API Tokens
2. Click on your API token
3. Verify these permissions are enabled:
   - ✓ Object Read
   - ✓ Object Write
   - ✓ Bucket Read
4. If permissions changed, create a new token and update `.env`

---

### Issue: "Read access check failed: AccessDenied"

**Solution:** API token missing List Objects permission:
1. Create new API token with these permissions:
   - ✓ Object Read
   - ✓ Object Write
   - ✓ Bucket Read (required for listing)
2. Update `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` in `.env`

---

### Issue: "Write access check failed: AccessDenied"

**Solution:** API token missing Object Write permission:
1. Create new API token with permissions including:
   - ✓ Object Write
2. Update credentials in `.env`

---

### Issue: Server logs warning "Missing R2 configuration"

**Solution:** This is informational - R2 features won't work but other API features will. To enable R2, add the missing environment variables.

---

## API Integration Examples

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8001"

# Health check
response = requests.get(f"{BASE_URL}/api/v1/r2/health")
print(response.json())

# Test upload
response = requests.post(f"{BASE_URL}/api/v1/r2/test-upload")
print(response.json())
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8001";

// Health check
fetch(`${BASE_URL}/api/v1/r2/health`)
  .then(r => r.json())
  .then(data => console.log(data));

// Test upload
fetch(`${BASE_URL}/api/v1/r2/test-upload`, { method: "POST" })
  .then(r => r.json())
  .then(data => console.log(data));
```

### cURL

```bash
# Health check
curl -X GET http://localhost:8001/api/v1/r2/health | jq

# Test upload
curl -X POST http://localhost:8001/api/v1/r2/test-upload | jq
```

---

## Implementation Notes

### R2 Service (`app/core/r2.py`)

Provides the core R2 functionality:
- `validate_credentials()`: Checks environment variables
- `validate_bucket_access()`: Verifies bucket exists
- `validate_read_access()`: Confirms list permission
- `validate_write_access()`: Tests upload/delete cycle
- `upload_file()`: Upload files to R2
- `delete_file()`: Delete files from R2
- `file_exists()`: Check file presence
- `generate_presigned_url()`: Create temporary access URLs
- `get_public_url()`: Get permanent public URLs

All methods include comprehensive error handling with specific error codes.

### R2 Routes (`app/api/v1/r2.py`)

Provides REST endpoints:
- `GET /api/v1/r2/health`: Full system health check
- `POST /api/v1/r2/test-upload`: Write access test

Both endpoints return appropriate HTTP status codes:
- `200 OK`: Success
- `503 Service Unavailable`: R2 configuration/access issue

### Configuration (`app/core/config.py`)

Settings loaded from `.env`:
- R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME (required)
- R2_PUBLIC_URL (optional)

Optional variables will not block application startup but R2 features require all four.

---

## Security Notes

- ⚠️ **Never commit `.env` to version control** - it contains sensitive credentials
- ⚠️ **Use strong, randomly generated JWT_SECRET_KEY** (minimum 32 characters)
- ⚠️ **Rotate R2 API tokens regularly** following Cloudflare security best practices
- ✓ All API endpoints follow FastAPI security practices
- ✓ Temporary test files in `.validation/` folder are cleaned up automatically
- ✓ Presigned URLs have configurable expiration (default 1 hour)

---

## Performance Notes

- Health check includes write access test, which creates temporary file in R2 (~instant with CF edge)
- Expect response times: 200-500ms for health checks (depends on network)
- Test file cleanup is automatic - no manual intervention needed
- Validation runs at application startup to warn about missing config

---

## Next Steps

After verifying R2 health:
1. Integrate video upload endpoints with R2 backend
2. Configure CDN/custom domain for public file access
3. Set up lifecycle policies in R2 for automatic cleanup
4. Monitor R2 usage in Cloudflare dashboard

For more information about R2, see: https://developers.cloudflare.com/r2/
