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

    # Gemini Configuration
    GEMINI_VISION_API_KEY = os.getenv("GEMINI_VISION_API_KEY")
    VISION_MODEL_ID = os.getenv("VISION_MODEL_ID", "gemini-1.5-pro-latest")
    
    GEMINI_TEXT_API_KEY = os.getenv("GEMINI_TEXT_API_KEY")
    TEXT_MODEL_ID = os.getenv("TEXT_MODEL_ID", "gemini-1.5-flash")

    # DeepInfra Configuration
    DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
    DEEPINFRA_VISION_MODEL = os.getenv("DEEPINFRA_VISION_MODEL", "meta-llama/Llama-3.2-11B-Vision-Instruct")
    DEEPINFRA_TEXT_MODEL = os.getenv("DEEPINFRA_TEXT_MODEL", "meta-llama/Meta-Llama-3-70B-Instruct")
    DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"
    
    MAX_RETRIES = 3
    
    # Validation
    if API_PROVIDER == "google":
        if not GEMINI_VISION_API_KEY:
             raise ValueError("GEMINI_VISION_API_KEY is not set in environment variables.")
        if not GEMINI_TEXT_API_KEY:
             raise ValueError("GEMINI_TEXT_API_KEY is not set in environment variables.")
    elif API_PROVIDER == "deepinfra":
        if not DEEPINFRA_API_KEY:
             raise ValueError("DEEPINFRA_API_KEY is not set in environment variables.")
    else:
        raise ValueError(f"Unknown API_PROVIDER: {API_PROVIDER}. Must be 'google' or 'deepinfra'.")

settings = Settings()
