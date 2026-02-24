
import unittest
import os
import sqlite3
from vision_factory.state.db import BatchDatabase

class TestBatchDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_batch_state.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        # Ensure schema file exists for the test (it relies on relative path src/state/schema.sql)
        # We assume the test is run from root
        self.db = BatchDatabase(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_init_db(self):
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn("documents", tables)
            self.assertIn("pages", tables)

    def test_document_lifecycle(self):
        doc_id = "test_hash_123"
        filename = "test.pdf"
        filepath = "/tmp/test.pdf"
        
        # Register
        created = self.db.register_document(doc_id, filename, filepath)
        self.assertTrue(created)
        
        # Register duplicate
        created = self.db.register_document(doc_id, filename, filepath)
        self.assertFalse(created)
        
        # Get
        doc = self.db.get_document(doc_id)
        self.assertEqual(doc["filename"], filename)
        self.assertEqual(doc["status"], "PENDING")
        
        # Update
        self.db.update_document_status(doc_id, "PROCESSING")
        doc = self.db.get_document(doc_id)
        self.assertEqual(doc["status"], "PROCESSING")

    def test_page_tracking(self):
        doc_id = "doc_p1"
        self.db.register_document(doc_id, "p.pdf", "/tmp/p.pdf")
        
        # Init pages
        self.db.init_pages(doc_id, 3)
        pending = self.db.get_pending_pages(doc_id)
        self.assertEqual(len(pending), 3)
        self.assertEqual(pending, [1, 2, 3])
        
        # Update page 1
        page_res = {"foo": "bar"}
        self.db.update_page_result(doc_id, 1, "COMPLETED", result=page_res)
        
        pending = self.db.get_pending_pages(doc_id)
        self.assertEqual(pending, [2, 3])
        
        completed = self.db.get_completed_pages(doc_id)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0], page_res)

    def test_hash_computation(self):
        # Create dummy file
        with open("dummy_hash.txt", "w") as f:
            f.write("hello world")
        
        h = self.db.compute_file_hash("dummy_hash.txt")
        # sha256 of "hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        self.assertEqual(h, expected)
        
        os.remove("dummy_hash.txt")

if __name__ == "__main__":
    unittest.main()
