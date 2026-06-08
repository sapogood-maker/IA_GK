import boto3
import logging
from botocore.exceptions import ClientError
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class R2Service:
    """
    Cloudflare R2 service for managing video uploads.
    
    Uses boto3 with S3-compatible API endpoint.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.s3_client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize boto3 S3 client for Cloudflare R2."""
        if not all([
            self.settings.r2_account_id,
            self.settings.r2_access_key_id,
            self.settings.r2_secret_access_key,
            self.settings.r2_bucket_name
        ]):
            logger.warning("R2 credentials not fully configured. Service may not work.")
            return None
        
        endpoint_url = f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com"
        
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.settings.r2_access_key_id,
            aws_secret_access_key=self.settings.r2_secret_access_key,
            region_name="auto"
        )
    
    async def upload_file(self, file_path: str, r2_key: str, content_type: str = "video/mp4") -> bool:
        """
        Upload a file to R2.
        
        Args:
            file_path: Local file path
            r2_key: R2 object key (path in bucket)
            content_type: MIME type of the file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            logger.error("R2 client not initialized")
            return False
        
        try:
            with open(file_path, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.settings.r2_bucket_name,
                    Key=r2_key,
                    Body=f,
                    ContentType=content_type
                )
            logger.info(f"Successfully uploaded {r2_key} to R2")
            return True
        except ClientError as e:
            logger.error(f"Error uploading to R2: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to R2: {e}")
            return False
    
    async def delete_file(self, r2_key: str) -> bool:
        """
        Delete a file from R2.
        
        Args:
            r2_key: R2 object key (path in bucket)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            logger.error("R2 client not initialized")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.settings.r2_bucket_name,
                Key=r2_key
            )
            logger.info(f"Successfully deleted {r2_key} from R2")
            return True
        except ClientError as e:
            logger.error(f"Error deleting from R2: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from R2: {e}")
            return False
    
    async def generate_presigned_url(self, r2_key: str, expiration_seconds: int = 3600) -> str | None:
        """
        Generate a presigned URL for accessing a file in R2.
        
        Args:
            r2_key: R2 object key (path in bucket)
            expiration_seconds: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or None if error
        """
        if not self.s3_client:
            logger.error("R2 client not initialized")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.settings.r2_bucket_name,
                    "Key": r2_key
                },
                ExpiresIn=expiration_seconds
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None
    
    async def file_exists(self, r2_key: str) -> bool:
        """
        Check if a file exists in R2.
        
        Args:
            r2_key: R2 object key (path in bucket)
            
        Returns:
            True if file exists, False otherwise
        """
        if not self.s3_client:
            logger.error("R2 client not initialized")
            return False
        
        try:
            self.s3_client.head_object(
                Bucket=self.settings.r2_bucket_name,
                Key=r2_key
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking file existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence: {e}")
            return False
    
    def get_public_url(self, r2_key: str) -> str:
        """
        Get the public URL for a file in R2.
        
        Args:
            r2_key: R2 object key (path in bucket)
            
        Returns:
            Public URL for the file
        """
        if self.settings.r2_public_url:
            return f"{self.settings.r2_public_url}/{r2_key}"
        
        # Fallback: construct URL from account ID
        return f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com/{r2_key}"


def get_r2_service() -> R2Service:
    """Dependency injection for R2Service."""
    return R2Service()
