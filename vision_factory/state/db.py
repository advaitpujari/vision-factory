
import sqlite3
import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BatchDatabase:
    def __init__(self, db_path: str = "output/batch_state.db"):
        self.db_path = db_path
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                # Use absolute path for schema.sql relative to this file
                schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
                with open(schema_path, "r") as f:
                    conn.executescript(f.read())
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def compute_file_hash(self, filepath: str) -> str:
        """Computes SHA-256 hash of a file for idempotency."""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                # Read in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {filepath}: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                # Map row to dict - explicit mapping matching schema
                # id, filename, filepath, status, total_pages, created_at, updated_at, metadata
                return {
                    "id": row[0],
                    "filename": row[1],
                    "filepath": row[2],
                    "status": row[3],
                    "total_pages": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                    "metadata": json.loads(row[7]) if row[7] else {}
                }
            return None

    def register_document(self, doc_id: str, filename: str, filepath: str) -> bool:
        """
        Registers a new document if it doesn't exist.
        Returns True if created, False if existed.
        """
        with self._get_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO documents (id, filename, filepath) VALUES (?, ?, ?)",
                    (doc_id, filename, filepath)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def update_document_status(self, doc_id: str, status: str, metadata: Dict = None):
        with self._get_connection() as conn:
            if metadata:
                conn.execute(
                    "UPDATE documents SET status = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, json.dumps(metadata), doc_id)
                )
            else:
                 conn.execute(
                    "UPDATE documents SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, doc_id)
                )

    def get_page_status(self, doc_id: str, page_num: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, result_json, error_message, attempt_count FROM pages WHERE doc_id = ? AND page_num = ?",
                (doc_id, page_num)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "status": row[0],
                    "result_json": json.loads(row[1]) if row[1] else None,
                    "error_message": row[2],
                    "attempt_count": row[3]
                }
            return None

    def init_pages(self, doc_id: str, total_pages: int):
        """Initializes page records for a document."""
        with self._get_connection() as conn:
            # Check if pages exist already to allow idempotency on re-runs
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM pages WHERE doc_id = ?", (doc_id,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                data = [(doc_id, i+1) for i in range(total_pages)]
                conn.executemany(
                    "INSERT INTO pages (doc_id, page_num) VALUES (?, ?)",
                    data
                )
    
    def update_page_result(self, doc_id: str, page_num: int, status: str, result: Dict = None, error: str = None):
        with self._get_connection() as conn:
            result_json = json.dumps(result) if result else None
            conn.execute(
                """
                UPDATE pages 
                SET status = ?, result_json = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP, attempt_count = attempt_count + 1
                WHERE doc_id = ? AND page_num = ?
                """,
                (status, result_json, error, doc_id, page_num)
            )

    def get_completed_pages(self, doc_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT result_json FROM pages WHERE doc_id = ? AND status = 'COMPLETED' ORDER BY page_num ASC",
                (doc_id,)
            )
            rows = cursor.fetchall()
            return [json.loads(r[0]) for r in rows if r[0]]

    def get_pending_pages(self, doc_id: str) -> List[int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT page_num FROM pages WHERE doc_id = ? AND status != 'COMPLETED' ORDER BY page_num ASC",
                (doc_id,)
            )
            return [r[0] for r in cursor.fetchall()]
