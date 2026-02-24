import pytest
from unittest.mock import patch, MagicMock
from vision_factory.ingestion.converter import PDFIngestor
import os

def test_convert_success():
    with patch('src.ingestion.converter.convert_from_path') as mock_convert:
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image, mock_image]
        
        ingestor = PDFIngestor()
        # Mock os.path.exists to True
        with patch('os.path.exists', return_value=True):
            images = ingestor.convert("fake.pdf")
            
        assert len(images) == 2
        mock_convert.assert_called_once()

def test_convert_file_not_found():
    ingestor = PDFIngestor()
    with pytest.raises(FileNotFoundError):
        ingestor.convert("non_existent.pdf")
