
import os
import glob
import logging
from typing import List, Dict, Any
from datetime import datetime

from vision_factory.pipeline import VisionPipeline

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    Handles batch processing of PDF files in a directory.
    """
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.pipeline = VisionPipeline()
        self.stats: List[Dict[str, Any]] = []

    def run(self):
        """
        Scans input directory for PDFs and processes them.
        """
        if not os.path.isdir(self.input_dir):
            logger.error(f"Input directory not found: {self.input_dir}")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        pdf_files = glob.glob(os.path.join(self.input_dir, "*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.input_dir}")
            return

        logger.info(f"Found {len(pdf_files)} PDFs in {self.input_dir}. Starting batch processing...")

        for i, pdf_path in enumerate(pdf_files):
            file_name = os.path.basename(pdf_path)
            logger.info(f"[{i+1}/{len(pdf_files)}] Processing {file_name}...")
            
            base_name = os.path.splitext(file_name)[0]
            output_path = os.path.join(self.output_dir, f"{base_name}.json")
            
            result = {
                "filename": file_name,
                "status": "UNKNOWN",
                "pages": 0,
                "questions": 0,
                "issues": []
            }

            try:
                # Run pipeline
                pipeline_result = self.pipeline.process_pdf(pdf_path, output_path)
                
                if pipeline_result:
                    result.update({
                        "status": pipeline_result.get("status", "UNKNOWN"),
                        "pages": pipeline_result.get("total_pages", 0),
                        "questions": pipeline_result.get("questions_found", 0),
                        "issues": pipeline_result.get("validation_issues", [])
                    })
                    
                    if pipeline_result.get("error"):
                         result["status"] = "FAILED"
                         result["error"] = pipeline_result["error"]

            except Exception as e:
                logger.error(f"Critical failure processing {file_name}: {e}")
                result["status"] = "CRITICAL_ERROR"
                result["error"] = str(e)
            
            self.stats.append(result)

        self._generate_report()

    def _generate_report(self):
        """
        Generates:
        1. Overview Report (Markdown)
        2. Detailed Log (CSV)
        """
        # 1. Detailed CSV Log
        csv_path = os.path.join(self.output_dir, "batch_details.csv")
        with open(csv_path, "w") as f:
            f.write("Filename,Status,TotalPages,Questions,IssuesCount,Error\n")
            for stat in self.stats:
                err = stat.get('error', '').replace(',', ';').replace('\n', ' ')
                f.write(f"{stat['filename']},{stat['status']},{stat['pages']},{stat['questions']},{len(stat['issues'])},{err}\n")

        # 2. Overview Report
        report_lines = []
        report_lines.append("# Batch Processing Overview")
        report_lines.append(f"Date: {datetime.now().isoformat()}")
        report_lines.append(f"Total Files: {len(self.stats)}")
        success_count = sum(1 for s in self.stats if s['status'] == 'VALIDATED')
        retry_count = sum(1 for s in self.stats if s['status'] in ['RETRY_NEEDED', 'PARTIAL_FAILURE']) # Assuming we map these
        report_lines.append(f"Success: {success_count} | Retries Needed: {retry_count}")
        report_lines.append("")
        
        # Table Header
        headers = ["Filename", "Status", "Pages", "Qs", "Issues"]
        
        header_row = f"| {headers[0]:<30} | {headers[1]:<20} | {headers[2]:<8} | {headers[3]:<5} | {headers[4]:<10} |"
        divider = f"|{'-'*32}|{'-'*22}|{'-'*10}|{'-'*7}|{'-'*12}|"
        
        report_lines.append(header_row)
        report_lines.append(divider)
        
        print("\n" + "="*80)
        print("BATCH PROCESSING SUMMARY")
        print("="*80)
        print(f"{headers[0]:<30} {headers[1]:<20} {headers[2]:<8} {headers[3]:<5} {headers[4]:<10}")
        print("-" * 80)

        for stat in self.stats:
            issues_count = len(stat['issues'])
            row_md = f"| {stat['filename']:<30} | {stat['status']:<20} | {stat['pages']:<8} | {stat['questions']:<5} | {issues_count:<10} |"
            report_lines.append(row_md)
            
            print(f"{stat['filename']:<30} {stat['status']:<20} {stat['pages']:<8} {stat['questions']:<5} {issues_count:<10}")

        summary_path = os.path.join(self.output_dir, "batch_overview.md")
        with open(summary_path, "w") as f:
            f.write("\n".join(report_lines))
            
        print("="*80)
        print(f"Overview: {summary_path}")
        print(f"Detailed Log: {csv_path}")
