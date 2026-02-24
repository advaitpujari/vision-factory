
import json
import logging
from typing import Optional, Dict, Any, List
import re
from vision_factory.output.models import PageOutput, Question, Option

logger = logging.getLogger(__name__)

class JSONParser:
    def __init__(self):
        pass

    def parse(self, raw_response: str) -> Optional[PageOutput]:
        """
        Parses the raw LLM response into a validated PageOutput object.
        """
        try:
            # 1. Clean Markdown
            cleaned_json = self._clean_markdown(raw_response)
            
            # 2. Load JSON
            data = json.loads(cleaned_json)
            
            # 3. Validate
            # We allow dynamic fields from the LLM, but we must map them to our strict schema
            # This step might need custom logic to map "diagram_bbox" to what we need
            
            return PageOutput(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            logger.debug(f"Raw Response: {raw_response}")
            # Optional: Implement a retry/repair mechanism here
            return None
        except Exception as e:
            logger.error(f"Validation Error: {e}")
            return None

    def _clean_markdown(self, text: str) -> str:
        """
        Removes ```json ... ``` blocks.
        """
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text.strip()
