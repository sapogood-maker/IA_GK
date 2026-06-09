from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import logging
import tempfile
import os

from app.core.r2 import get_r2_service, R2ValidationError, R2Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/r2", tags=["r2"])


class HealthResponse(BaseModel):
    status: str
    bucket: str
    read_access: bool
    write_access: bool


class TestUploadResponse(BaseModel):
    status: str
    message: str = None


@router.get("/health", response_model=HealthResponse)
async def r2_health(r2_service: R2Service = Depends(get_r2_service)):
    """
    Verify R2 configuration and access.
    
    Checks:
    - Authentication credentials are configured
    - Bucket exists and is accessible
    - Read access to bucket
    - Write access to bucket
    
    Returns:
        Health status with access information
    """
    try:
        # Validate credentials
        r2_service.validate_credentials()
        
        # Validate bucket access
        bucket_info = r2_service.validate_bucket_access()
        
        # Validate read access
        read_access = await r2_service.validate_read_access()
        
        # Validate write access
        write_access = await r2_service.validate_write_access()
        
        return HealthResponse(
            status="ok",
            bucket=r2_service.settings.r2_bucket_name,
            read_access=read_access,
            write_access=write_access
        )
    
    except R2ValidationError as e:
        logger.error(f"R2 validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during R2 health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during health check"
        )


@router.post("/test-upload", response_model=TestUploadResponse)
async def r2_test_upload(r2_service: R2Service = Depends(get_r2_service)):
    """
    Test R2 write access by uploading and deleting a test file.
    
    Steps:
    1. Create a temporary file
    2. Upload it to R2
    3. Verify it exists
    4. Delete it
    5. Verify deletion
    
    Returns:
        Success status
    """
    temp_file_path = None
    test_key = ".validation/test-upload.tmp"
    
    try:
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp.write("R2 test upload validation")
            temp_file_path = tmp.name
        
        # Verify credentials first
        r2_service.validate_credentials()
        
        # Upload the file
        upload_success = await r2_service.upload_file(temp_file_path, test_key, content_type="text/plain")
        if not upload_success:
            raise Exception("Failed to upload test file")
        
        logger.info(f"Test file uploaded to {test_key}")
        
        # Verify file exists
        file_exists = await r2_service.file_exists(test_key)
        if not file_exists:
            raise Exception("Test file not found after upload")
        
        logger.info(f"Test file verified at {test_key}")
        
        # Delete the file
        delete_success = await r2_service.delete_file(test_key)
        if not delete_success:
            logger.warning("Failed to delete test file - may need manual cleanup")
            raise Exception("Failed to delete test file")
        
        logger.info(f"Test file deleted from {test_key}")
        
        # Verify deletion
        file_still_exists = await r2_service.file_exists(test_key)
        if file_still_exists:
            logger.warning("Test file still exists after deletion attempt")
            raise Exception("Test file still exists after deletion")
        
        logger.info("R2 test upload validation completed successfully")
        
        return TestUploadResponse(
            status="success",
            message="R2 write access verified successfully"
        )
    
    except R2ValidationError as e:
        logger.error(f"R2 validation error during test upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error during R2 test upload: {e}")
        # Try to clean up test file
        try:
            await r2_service.delete_file(test_key)
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up test file: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Test upload failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
