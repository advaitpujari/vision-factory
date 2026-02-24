
import os
import logging
from typing import List, Dict, Any
import json

from vision_factory.ingestion.converter import PDFIngestor
from vision_factory.extraction.client import DeepInfraClient
from vision_factory.extraction.parser import JSONParser
from vision_factory.assets.cropper import ImageCropper
from vision_factory.assets.uploader import S3Uploader
from vision_factory.state.manager import StateManager
from vision_factory.output.logger import log_page_status, log_validation_result, logger_instance
from vision_factory.output.models import PageOutput, Question, Option
from vision_factory.output.validator import JSONValidator

logger = logging.getLogger(__name__)

class VisionPipeline:
    def __init__(self):
        self.ingestor = PDFIngestor()
        self.client = DeepInfraClient()
        self.parser = JSONParser()
        self.cropper = ImageCropper()
        self.uploader = S3Uploader()
        self.state_manager = StateManager()
        self.validator = JSONValidator()

    def process_pdf(self, pdf_path: str, output_path: str):
        """
        Runs the full Vision-to-JSON pipeline on a PDF.
        """
        from vision_factory.state.db import BatchDatabase
        db = BatchDatabase()
        
        logger.info(f"Starting pipeline for {pdf_path}")
        
        # 0. Hash & Register
        try:
            file_hash = db.compute_file_hash(pdf_path)
            doc_id = file_hash  # Use hash as ID for idempotency
            filename = os.path.basename(pdf_path)
            db.register_document(doc_id, filename, pdf_path)
            db.update_document_status(doc_id, "PROCESSING")
        except Exception as e:
            logger.error(f"Failed to initialize DB state: {e}")
            # Fallback to filename based ID if DB fails (or re-raise?)
            # For robustness, we'll try to proceed but logging will be limited
            doc_id = os.path.splitext(filename)[0]

        # 1. Ingest
        try:
            images = self.ingestor.convert(pdf_path)
            db.init_pages(doc_id, len(images))
        except Exception as e:
            logger.critical(f"Failed to ingest PDF: {e}")
            db.update_document_status(doc_id, "FAILED")
            return {
                "status": "FAILED",
                "total_pages": 0,
                "questions_found": 0,
                "validation_issues": [],
                "error": str(e)
            }

        all_questions: List[Question] = []
        total_pages = len(images)

        # 2. Process Pages
        for i, image in enumerate(images):
            page_num = i + 1
            logger.info(f"Processing Page {page_num}/{total_pages}...")
            
            try:
                # Check DB for cache
                page_status = db.get_page_status(doc_id, page_num)
                page_output = None
                
                if page_status and page_status['status'] == 'COMPLETED' and page_status['result_json']:
                    logger.info(f"Page {page_num} found in cache. Loading...")
                    try:
                        page_output = PageOutput(**page_status['result_json'])
                        log_page_status(doc_id, page_num, "CACHED", len(page_output.questions))
                    except Exception as parse_err:
                        logger.warning(f"Failed to load cached page {page_num}: {parse_err}. Reprocessing.")
                        page_output = None

                if not page_output:
                    # A. Extract (Vision API)
                    doc_name_clean = os.path.splitext(os.path.basename(pdf_path))[0]
                    # We pass the clean filename so the folder structure uses the name, not the hash
                    raw_response = self.client.extract_page(image, page_num, doc_name_clean)
                    if not raw_response:
                        log_page_status(doc_id, page_num, "FAILED", 0, "API returned empty response")
                        db.update_page_result(doc_id, page_num, "FAILED", error="Empty API Response")
                        continue
                    
                    # B. Parse
                    page_output = self.parser.parse(raw_response)
                    if not page_output:
                        log_page_status(doc_id, page_num, "FAILED", 0, "Failed to parse JSON")
                        db.update_page_result(doc_id, page_num, "FAILED", error="Parse Failure")
                        continue
                    
                    # Cache the successful parse result
                    db.update_page_result(doc_id, page_num, "COMPLETED", result=page_output.model_dump())

                # Capture metadata from first page
                if i == 0 and not hasattr(self, 'extracted_test_metadata'):
                     self.extracted_test_metadata = page_output.test_metadata.model_dump()
                
                # C. Asset Processing (Crop & Upload)
                self._process_assets(page_output, image, doc_id, page_num)
                
                # Update cache again if assets modified the object (urls added)
                # Optimization: Only update if changed? For safety, update.
                db.update_page_result(doc_id, page_num, "COMPLETED", result=page_output.model_dump())
                
                # D. State Management (Merge incomplete questions)
                completed_questions = self.state_manager.process_page_output(page_output)
                
                count = len(completed_questions)
                all_questions.extend(completed_questions)
                
                if not page_status or page_status['status'] != 'COMPLETED':
                     log_page_status(doc_id, page_num, "SUCCESS", count)
                
                log_page_status(doc_id, page_num, "SUCCESS", count)
                
            except Exception as e:
                # Analyze error type for Smart Retry
                error_msg = str(e)
                status_code = "FAILED" # Default to permanent failure
                
                # Check for Rate Limits or Transient errors
                # We check string because importing specific exceptions from google.api_core might vary
                if "ResourceExhausted" in error_msg or "ServiceUnavailable" in error_msg or "429" in error_msg or "503" in error_msg:
                    status_code = "RETRY_NEEDED"
                    logger.warning(f"Transient error on Page {page_num}: {e}. Marking for retry.")
                elif "RetryError" in error_msg: # Tenacity RetryError usually wraps the above
                     status_code = "RETRY_NEEDED"
                     logger.warning(f"Max retries exceeded on Page {page_num}. Marking for later retry.")
                else:
                    logger.error(f"Permanent error processing page {page_num}: {e}")

                log_page_status(doc_id, page_num, "CRITICAL_ERROR", 0, error_msg)
                db.update_page_result(doc_id, page_num, status_code, error=error_msg)
                # Continue to next page to maximize partial success
                continue

        # 3. Final Assembly
        # Check if any pending question remains in state
        if self.state_manager.pending_question:
            # Append as is, maybe flag incomplete
            all_questions.append(self.state_manager.pending_question)
            logger.warning("Pipeline finished with one pending incomplete question.")

        # Aggregate metadata (taking from first page or empty if none)
        #Ideally we should merge, but first page usually has the title
        test_metadata = {"title": None, "subject": None, "chapter": None, "estimated_duration_mins": None, "total_marks": None}
        
        # We need to access the metadata from the first page output, but we don't store page_outputs.
        # We can simulate it or just use empty for now if we didn't save it.
        # BETTER: Initialize it at the start of the loop
        
        final_output = {
             "test_metadata": self.extracted_test_metadata if hasattr(self, 'extracted_test_metadata') else test_metadata,
             "questions": [q.model_dump() for q in all_questions]
        }
        
        # 4. Validation
        logger.info("Running Sanity Checks on final JSON...")
        final_output, issues = self.validator.validate(final_output)
        
        # Log validation results
        status = "VALIDATED"
        if any(i['type'] in ['ERROR', 'CRITICAL'] for i in issues):
            status = "VALIDATION_FAILED"
        elif issues:
            status = "VALIDATION_WARNINGS"
            
        log_validation_result(doc_id, status, issues)
        db.update_document_status(doc_id, status, metadata=final_output.get("test_metadata"))

        if status == "VALIDATION_FAILED":
            logger.error(f"Validation failed with {len(issues)} issues. Check logs.")
        else:
            logger.info(f"Validation passed with {len(issues)} warnings.")

        # 5. Save
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=2)
        
        logger.info(f"Pipeline complete. Output saved to {output_path}")

        return {
            "status": status,
            "total_pages": total_pages,
            "questions_found": len(all_questions),
            "validation_issues": issues
        }

    def _process_assets(self, page_output: PageOutput, original_image, pdf_id: str, page_num: int):
        """
        Iterates through questions and options, crops diagrams, uploads them, and updates URL fields.
        """
        for q_idx, question in enumerate(page_output.questions):
            # 1. Question Diagram
            # New structure: bbox is in question.metadata.bbox
            if question.metadata and question.metadata.bbox:
                # Skip if already uploaded (from cache)
                if question.image_path and question.image_path.startswith("http"):
                    continue

                bbox = question.metadata.bbox
                logger.info(f"Processing diagram for Q{question.id}")
                try:
                    asset_name = f"q{question.id}_diagram_p{page_num}_{pdf_id[:8]}"
                    cropped = self.cropper.crop_and_optimize(original_image, bbox, asset_name)
                    url = self.uploader.upload_asset(cropped, pdf_id, asset_name)
                    if url:
                        question.image_path = url
                except Exception as e:
                    logger.error(f"Failed to process diagram for Q{question.id}: {e}")

            # 2. Options (Dictionary)
            # question.options is now Dict[str, Option]
            for opt_key, option in question.options.items():
                if option.is_image or option.bbox:
                    # Skip if already uploaded
                    if option.image_path and option.image_path.startswith("http"):
                        continue

                    # check if bbox is present
                    opt_bbox = option.bbox
                    if opt_bbox:
                        try:
                            # Use opt_key (A, B, C...) in asset name
                            asset_name = f"q{question.id}_opt{opt_key}_p{page_num}_{pdf_id[:8]}"
                            cropped = self.cropper.crop_and_optimize(original_image, opt_bbox, asset_name)
                            url = self.uploader.upload_asset(cropped, pdf_id, asset_name)
                            if url:
                                option.image_path = url
                        except Exception as e:
                             logger.error(f"Failed to process option {opt_key} for Q{question.id}: {e}")
