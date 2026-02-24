from pdf2image import convert_from_path
from PIL import Image
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)

class PDFIngestor:
    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def convert(self, pdf_path: str, output_folder: Optional[str] = None) -> List[Image.Image]:
        """
        Converts a PDF into a list of PIL Images at high DPI.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        logger.info(f"Converting PDF: {pdf_path} at {self.dpi} DPI")
        
        try:
            images = convert_from_path(pdf_path, dpi=self.dpi)
            logger.info(f"Successfully converted {len(images)} pages.")
            
            if output_folder:
                os.makedirs(output_folder, exist_ok=True)
                for i, img in enumerate(images):
                    img_path = os.path.join(output_folder, f"page_{i+1}.png")
                    img.save(img_path, "PNG")
                    logger.debug(f"Saved page {i+1} to {img_path}")
            
            return images
        except Exception as e:
            logger.error(f"Failed to convert PDF: {str(e)}")
            raise
