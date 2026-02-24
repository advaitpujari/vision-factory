
import re
from typing import Dict, List, Any, Optional, Tuple

class JSONValidator:
    """
    Sanity Check layer for generated JSON data.
    Ensures structural integrity, content quality, and logical consistency.
    """

    def validate(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Main validation entry point.
        Returns:
            - cleaned_data: The (potentially modified) data object.
            - issues: A list of dicts describing warnings/errors found.
              format: {"type": "ERROR"|"WARNING", "id": "q_id", "message": "..."}
        """
        issues = []
        
        # 1. Structural Checks
        if not self._validate_structure(data, issues):
            return data, issues # Critical failure, return immediately

        cleaned_questions = []
        seen_ids = set()

        for q in data.get("questions", []):
            q_id = q.get("id", "unknown")
            
            # ID Uniqueness
            if q_id in seen_ids:
                issues.append({"type": "ERROR", "id": q_id, "message": f"Duplicate Question ID: {q_id}"})
                continue # Skip duplicate
            seen_ids.add(q_id)

            # 2. Required Fields
            if not self._validate_required_fields(q, issues):
                continue # Skip malformed question

            # 3. Content & LaTeX
            if not self._validate_content(q, issues):
                continue # Skip empty/trash questions

            # 4. Logical Consistency
            self._validate_logic(q, issues)

            # 5. Type Enforcement & Null Handling
            self._enforce_types(q)

            cleaned_questions.append(q)

        data["questions"] = cleaned_questions
        
        # Update metadata total count matches actual questions
        if "test_metadata" in data and isinstance(data["test_metadata"], dict):
            data["test_metadata"]["total_questions"] = len(cleaned_questions)
            
        return data, issues

    def _validate_structure(self, data: Dict, issues: List) -> bool:
        if not isinstance(data, dict):
            issues.append({"type": "CRITICAL", "id": "ROOT", "message": "Root is not a JSON object"})
            return False
        
        required_keys = ["test_metadata", "questions"]
        for key in required_keys:
            if key not in data:
                issues.append({"type": "CRITICAL", "id": "ROOT", "message": f"Missing root key: {key}"})
                return False
                
        if not isinstance(data["questions"], list):
            issues.append({"type": "CRITICAL", "id": "ROOT", "message": "'questions' must be a list"})
            return False
            
        return True

    def _validate_required_fields(self, q: Dict, issues: List) -> bool:
        required = ["id", "text", "type", "options"]
        missing = [key for key in required if key not in q or q[key] is None]
        
        if missing:
            issues.append({"type": "ERROR", "id": q.get("id", "?"), "message": f"Missing required fields: {missing}"})
            return False
            
        # Validate options structure (must be dict with 4 keys usually, but at least not empty)
        if not isinstance(q["options"], dict):
             issues.append({"type": "ERROR", "id": q.get("id", "?"), "message": "'options' must be a dictionary"})
             return False
             
        return True

    def _validate_content(self, q: Dict, issues: List) -> bool:
        text = q.get("text", "")
        q_id = q.get("id", "?")
        
        # Empty/Short text scrubbing
        if not text or len(text.strip()) < 5:
             issues.append({"type": "WARNING", "id": q_id, "message": "Question text too short/empty. Removing."})
             return False

        # Trash Filtering
        trash_patterns = [
            r"^\s*-\s*\d+\s*-\s*$", # Page numbers like "- 12 -"
            r"(?i)CONFIDENTIAL",
            r"(?i)Page \d+ of \d+",
            r"^\s*Question\s*\d+\s*:?\s*$" # Bare "Question 1" headers
        ]
        for pattern in trash_patterns:
            if re.search(pattern, text):
                issues.append({"type": "WARNING", "id": q_id, "message": f"Detected trash content: '{pattern}'. Removing."})
                return False

        # LaTeX Balance
        if not self._check_latex_balance(text):
             issues.append({"type": "WARNING", "id": q_id, "message": "Unbalanced LaTeX delimiters ($) in text."})
             # We warn but don't delete for this, usually readable

        return True

    def _validate_logic(self, q: Dict, issues: List):
        q_id = q["id"]
        options = q["options"]
        correct = q.get("correct_option")

        # Correct option validity
        if correct:
            if correct not in options:
                 issues.append({"type": "ERROR", "id": q_id, "message": f"correct_option '{correct}' not found in options keys {list(options.keys())}"})
                 q["correct_option"] = None # Reset invalid choice
        
        # Option deduplication & Content
        seen_opt_texts = set()
        for key, opt in options.items():
            opt_text = opt.get("text")
            if opt_text:
                if opt_text in seen_opt_texts:
                     issues.append({"type": "WARNING", "id": q_id, "message": f"Duplicate option text found in {key}"})
                seen_opt_texts.add(opt_text)
                
                # Check Latex in options
                if not self._check_latex_balance(opt_text):
                     issues.append({"type": "WARNING", "id": q_id, "message": f"Unbalanced LaTeX in option {key}"})

        # BBox Reality Check
        if q.get("metadata") and q["metadata"].get("bbox"):
            bbox = q["metadata"]["bbox"]
            if not self._is_valid_bbox(bbox):
                 issues.append({"type": "WARNING", "id": q_id, "message": f"Invalid BBox: {bbox}"})
                 q["metadata"]["bbox"] = None

    def _enforce_types(self, q: Dict):
        # Nullable handling
        nullable_fields = ["explanation", "image_path", "is_trap", "difficulty", "ideal_time_seconds", "subject_tag"]
        for field in nullable_fields:
            if field in q and (q[field] == "null" or q[field] == ""):
                q[field] = None

        # Integer casting
        if q.get("ideal_time_seconds"):
            try:
                q["ideal_time_seconds"] = int(q["ideal_time_seconds"])
            except:
                q["ideal_time_seconds"] = None

    def _check_latex_balance(self, text: str) -> bool:
        # Simple count of non-escaped $'s
        # This is a heuristic. 
        # A more robust check might negate \$ 
        if not text:
            return True
        dollar_count = text.count("$") - text.count("\\$")
        return dollar_count % 2 == 0

    def _is_valid_bbox(self, bbox: List) -> bool:
        if not isinstance(bbox, list) or len(bbox) != 4:
            return False
        ymin, xmin, ymax, xmax = bbox
        # Ensure numbers
        try:
            ymin, xmin, ymax, xmax = float(ymin), float(xmin), float(ymax), float(xmax)
        except:
            return False
            
        if ymin < 0 or xmin < 0: return False
        if ymin >= ymax or xmin >= xmax: return False
        return True
