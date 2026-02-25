import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    
    # Provider Configuration
    API_PROVIDER = os.getenv("API_PROVIDER", "google").lower() # 'google' or 'deepinfra'
    API_PROVIDER_URL = os.getenv("API_PROVIDER_URL", "https://api.deepinfra.com/v1/openai")

    # API Keys and Models
    VISION_API_KEY = os.getenv("VISION_API_KEY")
    VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME")
    
    TEXT_API_KEY = os.getenv("TEXT_API_KEY")
    TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME")
    
    MAX_RETRIES = 3
    
    # Validation
    if not VISION_API_KEY:
         raise ValueError("VISION_API_KEY is not set in environment variables.")
    if not TEXT_API_KEY:
         raise ValueError("TEXT_API_KEY is not set in environment variables.")

settings = Settings()
