# Video Upload Service Refactoring Report

## Summary
Removed placeholder implementation in `video_upload_service.py` that used truncated session UUID fragments. Implemented proper database-driven goalkeeper ID retrieval for R2 storage path generation.

---

## Files Modified

### 1. `backend_fastapi/app/services/video_upload_service.py`

#### Change 1: Refactored `_generate_r2_key` Method
**Location:** Lines 48-70

**Previous Implementation (Placeholder):**
```python
def _generate_r2_key(self, training_session_id: UUID, original_filename: str) -> str:
    """Generate R2 storage key..."""
    timestamp = datetime.utcnow()
    year = timestamp.year
    month = f"{timestamp.month:02d}"
    
    # Placeholder using session UUID fragment
    gk_id = training_session_id.hex[:8]
    
    file_ext = Path(original_filename).suffix.lower()
    base_name = Path(original_filename).stem
    unique_name = f"{base_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}{file_ext}"
    
    return f"videos/{gk_id}/{year}/{month}/{unique_name}"
```

**New Implementation (Database-Driven):**
```python
async def _generate_r2_key(self, training_session_id: UUID, original_filename: str) -> str:
    """
    Generate R2 storage key based on structure: videos/goalkeeper_id/year/month/filename
    
    Retrieves the actual goalkeeper_id from the training session.
    """
    timestamp = datetime.utcnow()
    year = timestamp.year
    month = f"{timestamp.month:02d}"
    
    # Load training session from database to get actual goalkeeper_id
    session = await self.session_repo.get_by_id(training_session_id)
    if not session:
        raise ValueError(f"Training session {training_session_id} not found")
    
    goalkeeper_id = str(session.goalkeeper_id)
    
    # Generate unique filename
    file_ext = Path(original_filename).suffix.lower()
    base_name = Path(original_filename).stem
    unique_name = f"{base_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}{file_ext}"
    
    return f"videos/{goalkeeper_id}/{year}/{month}/{unique_name}"
```

**Key Changes:**
- ✅ Method signature changed from synchronous to `async`
- ✅ Added database query: `await self.session_repo.get_by_id(training_session_id)`
- ✅ Added error handling for missing training sessions
- ✅ Retrieves actual `goalkeeper_id` from TrainingSession model
- ✅ Removed placeholder: `training_session_id.hex[:8]`
- ✅ Updated documentation to explain database retrieval

#### Change 2: Updated Method Call in `upload_video`
**Location:** Line 114

**Previous Code:**
```python
r2_key = self._generate_r2_key(training_session_id, file.filename)
```

**Updated Code:**
```python
r2_key = await self._generate_r2_key(training_session_id, file.filename)
```

**Reason:** Method is now async and must be awaited.

---

## Behavior Changes

### Before
- Storage path used truncated session UUID: `videos/abc12345/2026/06/training.mp4`
- No actual goalkeeper association in path
- Placeholder solution

### After
- Storage path uses actual goalkeeper UUID: `videos/550e8400-e29b-41d4-a716-446655440000/2026/06/training_20260608_173852.mp4`
- Direct goalkeeper association in storage structure
- Database-backed, reliable identifier

---

## Storage Path Structure

**New Format:** `videos/{goalkeeper_id}/{year}/{month}/{filename}`

**Example:** 
```
videos/550e8400-e29b-41d4-a716-446655440000/2026/06/training_20260608_173852.mp4
```

**Components:**
- `{goalkeeper_id}`: Full UUID of the goalkeeper (retrieved from TrainingSession)
- `{year}`: 4-digit year (e.g., 2026)
- `{month}`: 2-digit zero-padded month (e.g., 06)
- `{filename}`: Original filename with timestamp: `{base}_{YYYYMMDD_HHMMSS}.{ext}`

---

## Error Handling

The new implementation includes robust error handling:

1. **Training Session Not Found:** Raises `ValueError` if the training session cannot be loaded
2. **Database Availability:** Relies on existing TrainingSessionRepository error handling
3. **UUID Conversion:** Safely converts UUID to string for path construction

---

## Database Dependencies

Uses existing repository infrastructure:
- **TrainingSessionRepository.get_by_id():** Fetches training session by ID
- **TrainingSession.goalkeeper_id:** Direct attribute access for goalkeeper UUID

---

## Testing Recommendations

1. **Unit Test:** Verify `_generate_r2_key` retrieves correct goalkeeper_id for known training sessions
2. **Integration Test:** Confirm video paths follow format: `videos/{uuid}/{year}/{month}/{filename}`
3. **Error Case:** Verify ValueError is raised when training session doesn't exist
4. **Async Handling:** Verify method properly awaits in upload_video context

---

## No Breaking Changes

- ✅ Public API of `upload_video` remains unchanged
- ✅ Existing error handling behavior preserved
- ✅ Video record creation unchanged
- ✅ R2 upload process unchanged
- ✅ Return values and response structure unchanged

---

## Migration Notes

- No database migrations required
- No existing data updates needed
- New videos will use the correct storage path automatically
- Existing videos remain unchanged in R2

---

**Status:** ✅ Complete
**Review Date:** 2026-06-08
