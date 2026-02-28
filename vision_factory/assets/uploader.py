
import boto3
from PIL import Image
from io import BytesIO
import logging
from typing import Optional
from botocore.exceptions import NoCredentialsError

from vision_factory.config.settings import settings

logger = logging.getLogger(__name__)

class S3Uploader:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET_NAME

    def upload_asset(self, image: Image.Image, pdf_id: str, asset_name: str) -> Optional[str]:
        """
        Uploads a PIL Image to S3 as WebP and returns the public URL.
        """
        try:
            buffer = BytesIO()
            image.save(buffer, format="WEBP", quality=80)
            buffer.seek(0)
            
            key = f"assets/{pdf_id}/{asset_name}.webp"
            
            self.s3_client.upload_fileobj(
                buffer, 
                self.bucket, 
                key, 
                ExtraArgs={'ContentType': 'image/webp'}
            )
            
            # Construct URL
            url = f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            logger.info(f"Uploaded asset to {url}")
            return url

        except NoCredentialsError:
            logger.error("AWS Credentials not found.")
            return None
        except Exception as e:
            logger.error(f"Failed to upload asset {asset_name}: {e}")
            return None
