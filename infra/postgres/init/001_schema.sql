-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Literature table (matches InMemory/SQLite schema - flattened PDF fields)
CREATE TABLE IF NOT EXISTS literature (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source TEXT NOT NULL,
    year INTEGER NOT NULL,
    snippet TEXT NOT NULL,
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    abstract TEXT,
    citation_url TEXT,
    pubmed_id TEXT,
    doi TEXT,
    pdf_upload_id TEXT,
    pdf_file_name TEXT,
    pdf_parse_status TEXT,
    pdf_parse_message TEXT,
    pdf_parse_started_at TEXT,
    pdf_parse_finished_at TEXT,
    pdf_parse_result JSONB,
    last_parse_trigger TEXT,
    parse_attempt_count INTEGER,
    related_entity_ids JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- Literature chunk table (matches existing chunk schema)
CREATE TABLE IF NOT EXISTS literature_chunk (
    chunk_id TEXT PRIMARY KEY,
    literature_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    section_title TEXT,
    evidence_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(128),
    created_at TEXT NOT NULL,
    FOREIGN KEY (literature_id) REFERENCES literature(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunk_literature_id ON literature_chunk(literature_id);
CREATE INDEX IF NOT EXISTS idx_chunk_embedding ON literature_chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Network task table (matches existing network task schema)
CREATE TABLE IF NOT EXISTS network_task (
    task_id TEXT PRIMARY KEY,
    indication_keywords JSONB NOT NULL,
    tcm_indication TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    result JSONB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_network_task_status ON network_task(status);
