
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision_factory.pipeline import VisionPipeline
from vision_factory.output.logger import setup_logging

def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Configuration
    INPUT_PDF = "sample.pdf"
    OUTPUT_JSON = "output.json"

    # Validate input
    if not os.path.exists(INPUT_PDF):
        logger.error(f"Input file not found: {INPUT_PDF}")
        return

    # Initialize and Run Pipeline
    try:
        pipeline = VisionPipeline()
        pipeline.process_pdf(INPUT_PDF, OUTPUT_JSON)
        logger.info("Pipeline execution finished.")
    except Exception as e:
        logger.critical(f"Pipeline crashed: {e}")
        raise

if __name__ == "__main__":
    main()
