
import logging
import json
from datetime import datetime
from typing import Any, Dict
import sys

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

class JSONLogHandler:
    def __init__(self, log_file: str = None):
        if log_file:
             self.log_file = log_file
        else:
             # Ensure output directory exists before writing logs
             import os
             os.makedirs("output", exist_ok=True)
             self.log_file = f"output/processing_log_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    def log(self, entry: Dict[str, Any]):
        """
        Logs a structured dictionary as a JSON line.
        """
        entry["timestamp"] = datetime.now().isoformat()
        
        # Console output
        print(f"[{entry.get('status', 'INFO')}] Page {entry.get('page', '?')}: {entry.get('message', '')}")
        
        # File output
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")

logger_instance = JSONLogHandler()

def log_page_status(pdf_id: str, page: int, status: str, extracted_count: int, message: str = ""):
    logger_instance.log({
        "pdf_id": pdf_id,
        "page": page,
        "status": status,
        "questions_extracted": extracted_count,
    })

def log_validation_result(pdf_id: str, status: str, issues: list):
    """
    Logs the result of the JSON validation step.
    issues: List of dicts {"type": "ERROR", "id": "...", "message": "..."}
    """
    error_count = sum(1 for i in issues if i['type'] in ['ERROR', 'CRITICAL'])
    warning_count = sum(1 for i in issues if i['type'] == 'WARNING')
    
    logger_instance.log({
        "pdf_id": pdf_id,
        "page": "ALL",
        "status": status, # VALIDATED / VALIDATION_FAILED / VALIDATION_WARNINGS
        "message": f"Validation complete. Errors: {error_count}, Warnings: {warning_count}",
        "validation_issues": issues
    })
