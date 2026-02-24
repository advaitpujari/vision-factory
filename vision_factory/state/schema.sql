
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,          -- SHA-256 Hash of the file content
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED, PARTIAL_SUCCESS
    total_pages INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON                  -- Extracted test metadata
);

CREATE TABLE IF NOT EXISTS pages (
    doc_id TEXT NOT NULL,
    page_num INTEGER NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED, RETRY_NEEDED
    result_json TEXT,              -- The JSON output for this page
    error_message TEXT,
    attempt_count INTEGER DEFAULT 0,
    metrics JSON,                  -- Token usage, latency, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id, page_num),
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status);
