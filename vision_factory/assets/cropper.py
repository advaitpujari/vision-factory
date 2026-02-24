
from PIL import Image
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class ImageCropper:
    def __init__(self, padding: int = 20):
        self.padding = padding

    def crop_and_optimize(self, 
                          original_image: Image.Image, 
                          bbox: List[int], 
                          description: str = "asset") -> Image.Image:
        """
        Crops the image based on bbox [ymin, xmin, ymax, xmax] (0-1000 scale).
        Adds padding and converts to WebP format optimized in-memory.
        """
        width, height = original_image.size
        
        # Unpack and denormalize
        ymin_n, xmin_n, ymax_n, xmax_n = bbox
        
        ymin = int((ymin_n / 1000) * height)
        xmin = int((xmin_n / 1000) * width)
        ymax = int((ymax_n / 1000) * height)
        xmax = int((xmax_n / 1000) * width)

        # Apply padding
        ymin = max(0, ymin - self.padding)
        xmin = max(0, xmin - self.padding)
        ymax = min(height, ymax + self.padding)
        xmax = min(width, xmax + self.padding)

        # Validate crop dimensions
        if xmax <= xmin or ymax <= ymin:
            logger.warning(f"Invalid crop dimensions for {description}: {bbox}. Returning original image fallback.")
            return original_image

        try:
            cropped_img = original_image.crop((xmin, ymin, xmax, ymax))
            return cropped_img
        except Exception as e:
            logger.error(f"Failed to crop {description}: {e}")
            raise
