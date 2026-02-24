
import google.generativeai as genai
import os
from vision_factory.config.settings import settings

def list_models():
    genai.configure(api_key=settings.GEMINI_VISION_API_KEY)
    print("Listing models for VISION KEY...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

if __name__ == "__main__":
    list_models()
