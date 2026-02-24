import argparse
import logging
import os
import sys
from dotenv import load_dotenv

# Load env before importing pipeline settings
load_dotenv()

from vision_factory.pipeline import VisionPipeline
from vision_factory.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Vision-to-JSON Factory Pipeline")
    parser.add_argument("--input", "-i", help="Path to the PDF file or directory to process", default="input")
    parser.add_argument("--output", "-o", help="Path to the output directory", default="output")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)

    if os.path.isdir(args.input):
        # Batch Mode
        # If output is not specified, default to input_dir/processed_json
        # BUT now we default to 'output' arg which is 'output/' by default.
            
        from vision_factory.batch_processor import BatchProcessor
        # BatchProcessor expects (input_dir, output_dir)
        processor = BatchProcessor(args.input, args.output)
        processor.run()
        
    else:
        # Single File Mode
        if not os.path.exists(args.input):
            logger.error(f"File not found: {args.input}")
            sys.exit(1)

        # Determine output file path
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_file_path = os.path.join(args.output, f"{base_name}.json")

        try:
            pipeline = VisionPipeline()
            pipeline.process_pdf(args.input, output_file_path)
        except Exception as e:
            logger.critical(f"Pipeline failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
