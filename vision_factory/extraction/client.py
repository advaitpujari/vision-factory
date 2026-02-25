import google.generativeai as genai
import os
import logging
import base64
import requests
from io import BytesIO
from typing import Optional, List, Dict, Any
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

from vision_factory.config.settings import settings
from vision_factory.extraction.prompt import VISION_MARKDOWN_PROMPT, MARKDOWN_TO_JSON_PROMPT

logger = logging.getLogger(__name__)

class DeepInfraClient:
    """
    Wrapper for LLM Extraction implementing a Two-Step process:
    1. Vision Model -> Markdown (content + layout)
    2. Text Model -> JSON (structure)
    
    Supports:
    - Google Gemini (Native SDK)
    - DeepInfra (OpenAI-compatible API)
    """
    def __init__(self):
        self.provider = settings.API_PROVIDER
        self.base_processed_dir = os.path.join(os.getcwd(), "output", "processed_json") # Updated to output dir
        os.makedirs(self.base_processed_dir, exist_ok=True)

        if self.provider == "google":
            self._configure_google()
        elif self.provider == "deepinfra":
            self._configure_deepinfra()
            
    def _configure_google(self):
        try:
            genai.configure(api_key=settings.VISION_API_KEY)
            self.vision_model_id = settings.VISION_MODEL_NAME or "gemini-1.5-pro-latest"
            self.text_model_id = settings.TEXT_MODEL_NAME or "gemini-1.5-flash"
            self.vision_key = settings.VISION_API_KEY
            self.text_key = settings.TEXT_API_KEY
        except Exception as e:
            logger.error(f"Failed to configure Google Gemini: {e}")

    def _configure_deepinfra(self):
        self.api_key = settings.VISION_API_KEY # Assuming same key for both
        self.base_url = settings.API_PROVIDER_URL
        self.vision_model_id = settings.VISION_MODEL_NAME or "meta-llama/Llama-3.2-11B-Vision-Instruct"
        self.text_model_id = settings.TEXT_MODEL_NAME or "meta-llama/Meta-Llama-3-70B-Instruct"
        
        if not self.api_key:
             logger.error("DeepInfra API Key missing!")

    def extract_page(self, image: Image.Image, page_num: int, doc_name: str) -> Optional[str]:
        """
        Orchestrates the two-step extraction process with caching.
        Returns the final JSON string.
        """
        # Setup directories for this specific doc
        # doc_name is passed as the ID/Hash from pipeline.py.
        # However, the user wants folders named after the file.
        # We need to change how extract_page is called or how we use doc_name.
        # For now, let's assume doc_name MIGHT be the hash.
        
        doc_dir = os.path.join(self.base_processed_dir, doc_name)
        markdown_dir = os.path.join(doc_dir, "markdown")
        json_dir = os.path.join(doc_dir, "json")
        
        os.makedirs(markdown_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)

        # Step 1: Vision -> Markdown
        markdown_content = self._step_1_vision_to_markdown(image, page_num, markdown_dir, doc_name)
        if not markdown_content:
            return None
            
        # Step 2: Markdown -> JSON
        json_content = self._step_2_markdown_to_json(markdown_content, page_num, json_dir, doc_name)
        return json_content

    def _image_to_base64(self, image: Image.Image) -> str:
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    def _step_1_vision_to_markdown(self, image: Image.Image, page_num: int, output_dir: str, doc_name: str) -> Optional[str]:
        cache_file = os.path.join(output_dir, f"{doc_name}_page_{page_num}.md")
        
        if os.path.exists(cache_file):
            logger.info(f"[Step 1] Using cached Markdown for page {page_num}")
            with open(cache_file, "r") as f:
                return f.read()

        logger.info(f"[Step 1] Sending Page {page_num} to Vision Model ({self.vision_model_id})...")
        
        try:
            if self.provider == "google":
                return self._call_google_vision(image, VISION_MARKDOWN_PROMPT, cache_file)
            elif self.provider == "deepinfra":
                return self._call_deepinfra_vision(image, VISION_MARKDOWN_PROMPT, cache_file)
        except Exception as e:
            self._handle_error(e, page_num, 1)
            return None

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    def _step_2_markdown_to_json(self, markdown_content: str, page_num: int, output_dir: str, doc_name: str) -> Optional[str]:
        cache_file = os.path.join(output_dir, f"{doc_name}_page_{page_num}.json")
        
        if os.path.exists(cache_file):
            logger.info(f"[Step 2] Using cached JSON for page {page_num}")
            with open(cache_file, "r") as f:
                return f.read()

        logger.info(f"[Step 2] Sending Page {page_num} content to Text Model ({self.text_model_id})...")
        
        try:
             if self.provider == "google":
                 return self._call_google_text(markdown_content, MARKDOWN_TO_JSON_PROMPT, cache_file)
             elif self.provider == "deepinfra":
                 return self._call_deepinfra_text(markdown_content, MARKDOWN_TO_JSON_PROMPT, cache_file)
        except Exception as e:
            self._handle_error(e, page_num, 2)
            return None

    # --- GOOGLE IMPLEMENTATION ---
    def _call_google_vision(self, image, prompt, cache_file):
        genai.configure(api_key=self.vision_key)
        model = genai.GenerativeModel(self.vision_model_id)
        response = model.generate_content([prompt, image])
        cont = response.text
        self._save_cache(cache_file, cont)
        return cont

    def _call_google_text(self, content, system_prompt, cache_file):
        genai.configure(api_key=self.text_key)
        model = genai.GenerativeModel(self.text_model_id)
        response = model.generate_content([system_prompt, content])
        cont = response.text
        self._save_cache(cache_file, cont)
        return cont

    # --- DEEPINFRA IMPLEMENTATION ---
    def _call_deepinfra_vision(self, image, prompt, cache_file):
        b64_image = self._image_to_base64(image)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.vision_model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }
        
        resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
        resp.raise_for_status()
        result = resp.json()
        content = result['choices'][0]['message']['content']
        self._save_cache(cache_file, content)
        return content

    def _call_deepinfra_text(self, content, system_prompt, cache_file):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.text_model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }
        
        resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
        resp.raise_for_status()
        result = resp.json()
        text_content = result['choices'][0]['message']['content']
        self._save_cache(cache_file, text_content)
        return text_content
        
    def _save_cache(self, path, content):
        with open(path, "w") as f:
            f.write(content)

    def _handle_error(self, e, page_num, step):
        if "429" in str(e) or "quota" in str(e).lower():
            logger.warning(f"[Step {step}] Rate Limit hit for Page {page_num}, retrying... ({e})")
            raise e
        logger.error(f"[Step {step}] Failed: {e}")
        raise e
