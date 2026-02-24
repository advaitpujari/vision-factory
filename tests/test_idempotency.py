
import unittest
import os
import shutil
import sqlite3
import json
from unittest.mock import MagicMock, patch
from vision_factory.pipeline import VisionPipeline
from vision_factory.output.models import PageOutput, TestMetadata, Question

class TestPipelineIdempotency(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/test_data_idempotency"
        self.pdf_path = os.path.join(self.test_dir, "test.pdf")
        self.output_path = os.path.join(self.test_dir, "output.json")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create dummy PDF (needs to be valid enough for ingestor, but we'll mock ingestor)
        with open(self.pdf_path, "w") as f:
            f.write("dummy content for hash")

        # Clean DB
        if os.path.exists("batch_state.db"):
            os.remove("batch_state.db")

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        if os.path.exists("batch_state.db"):
            os.remove("batch_state.db")

    @patch("src.pipeline.PDFIngestor")
    @patch("src.pipeline.DeepInfraClient")
    def test_caching(self, MockClient, MockIngestor):
        # Setup Mocks
        mock_ingestor = MockIngestor.return_value
        # Mocking 2 pages (images)
        mock_ingestor.convert.return_value = ["img1", "img2"]
        
        mock_client = MockClient.return_value
        
        # Dummy PageOutput
        dummy_meta = TestMetadata(title="Test", subject="Sub", chapter="Ch", estimated_duration_mins=10, total_marks=10)
        # Fix: id must be str, metadata must not be None (use default or empty dict)
        dummy_q = Question(id="1", text="Q1", options={}, answer="A", explanation="Exp")
        dummy_output = PageOutput(test_metadata=dummy_meta, questions=[dummy_q])
        
        # Mock extract_page calls
        # We expect it to be called TWICE only (once for each page of the first run)
        mock_client.extract_page.return_value = {"mock": "response"} 
        
        # Mock Parser inside Pipeline? 
        # Since we can't easily patch the instance variable 'parser' after init without more complex patching,
        # let's patch the JSONParser class at the module level in the pipeline.
        with patch("src.pipeline.JSONParser") as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.parse.return_value = dummy_output

            # Run 1
            pipeline = VisionPipeline()
            # Disable Uploader/Cropper for speed/simplicity
            pipeline.cropper = MagicMock()
            pipeline.uploader = MagicMock()
            
            print("Running Pipeline 1st time...")
            pipeline.process_pdf(self.pdf_path, self.output_path)
            
            # Assert API calls made
            self.assertEqual(mock_client.extract_page.call_count, 2)
            
            # Reset mocks
            mock_client.extract_page.reset_mock()
            
            # Run 2 (Should use cache)
            print("Running Pipeline 2nd time...")
            result = pipeline.process_pdf(self.pdf_path, self.output_path)
            
            # Assert API calls SKIP
            self.assertEqual(mock_client.extract_page.call_count, 0)
            self.assertEqual(result['status'], "VALIDATION_FAILED")

            # Verify DB content
            conn = sqlite3.connect("batch_state.db")
            c = conn.cursor()
            c.execute("SELECT status FROM documents")
            self.assertEqual(c.fetchone()[0], "VALIDATION_FAILED")
            conn.close()

if __name__ == "__main__":
    unittest.main()
