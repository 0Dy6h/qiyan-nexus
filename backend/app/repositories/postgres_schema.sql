-- PostgreSQL schema for Qiyan Nexus runtime backend
-- Compatible with pgvector extension for vector similarity search

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Literature table
-- Stores literature items (sample, PubMed, CNKI, uploaded PDFs)
CREATE TABLE IF NOT EXISTS literature (
    id                    TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    language              TEXT NOT NULL,
    source_type           TEXT NOT NULL,
    source                TEXT NOT NULL,
    year                  INTEGER NOT NULL,
    snippet               TEXT NOT NULL,
    authors               JSONB NOT NULL DEFAULT '[]',
    keywords              JSONB NOT NULL DEFAULT '[]',
    evidence_tags         JSONB NOT NULL DEFAULT '[]',
    abstract              TEXT,
    citation_url          TEXT,
    pubmed_id             TEXT,
    doi                   TEXT,
    pdf_upload_id         TEXT,
    pdf_file_name         TEXT,
    pdf_parse_status      TEXT,
    pdf_parse_message     TEXT,
    pdf_parse_started_at  TIMESTAMP,
    pdf_parse_finished_at TIMESTAMP,
    pdf_parse_result      JSONB,
    last_parse_trigger    TEXT,
    parse_attempt_count   INTEGER,
    related_entity_ids    JSONB NOT NULL DEFAULT '[]',
    created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for literature table
CREATE INDEX IF NOT EXISTS idx_literature_source_type ON literature(source_type);
CREATE INDEX IF NOT EXISTS idx_literature_year ON literature(year DESC);
CREATE INDEX IF NOT EXISTS idx_literature_pubmed_id ON literature(pubmed_id) WHERE pubmed_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_literature_pdf_upload_id ON literature(pdf_upload_id) WHERE pdf_upload_id IS NOT NULL;

-- Chunks table
-- Stores evidence chunks from literature (section-level granularity)
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id           TEXT PRIMARY KEY,
    literature_id      TEXT NOT NULL REFERENCES literature(id) ON DELETE CASCADE,
    section            TEXT NOT NULL,
    text               TEXT NOT NULL,
    source_quote       TEXT NOT NULL,
    evidence_tags      JSONB NOT NULL DEFAULT '[]',
    related_entity_ids JSONB NOT NULL DEFAULT '[]',
    source_type        TEXT NOT NULL DEFAULT 'sample',
    pdf_upload_id      TEXT,
    embedding          vector(384),  -- BGE-small-zh-v1.5 dimension
    created_at         TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for chunks table
CREATE INDEX IF NOT EXISTS idx_chunks_literature_id ON chunks(literature_id);
-- IVFFlat index for vector similarity search (pgvector)
-- lists = 100 is reasonable for ~10k-100k chunks
-- Use vector_cosine_ops for cosine similarity (most common for embeddings)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Network tasks table
-- Stores network pharmacology analysis tasks and results
CREATE TABLE IF NOT EXISTS network_tasks (
    task_id       TEXT PRIMARY KEY,
    owner_id      TEXT,
    query         TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    status        TEXT NOT NULL,
    progress      INTEGER NOT NULL DEFAULT 0,
    poll_count    INTEGER NOT NULL DEFAULT 0,
    data_mode     TEXT NOT NULL DEFAULT 'mock',
    result        JSONB,
    error         TEXT,
    warnings      JSONB NOT NULL DEFAULT '[]',
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE network_tasks
    ADD COLUMN IF NOT EXISTS owner_id TEXT;
ALTER TABLE network_tasks
    ADD COLUMN IF NOT EXISTS data_mode TEXT NOT NULL DEFAULT 'mock';
ALTER TABLE network_tasks
    ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE network_tasks
    ADD COLUMN IF NOT EXISTS warnings JSONB NOT NULL DEFAULT '[]';

-- Indexes for network_tasks table
CREATE INDEX IF NOT EXISTS idx_network_tasks_status ON network_tasks(status);
CREATE INDEX IF NOT EXISTS idx_network_tasks_owner_id ON network_tasks(owner_id);
CREATE INDEX IF NOT EXISTS idx_network_tasks_created_at ON network_tasks(created_at DESC);

-- Helper function: update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: auto-update updated_at on literature updates
DROP TRIGGER IF EXISTS trigger_literature_updated_at ON literature;
CREATE TRIGGER trigger_literature_updated_at
    BEFORE UPDATE ON literature
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE literature IS 'Literature items from various sources (sample, PubMed, CNKI, uploaded PDFs)';
COMMENT ON TABLE chunks IS 'Evidence chunks extracted from literature at section level';
COMMENT ON TABLE network_tasks IS 'Network pharmacology analysis tasks and results';
COMMENT ON COLUMN chunks.embedding IS 'BGE-small-zh-v1.5 embedding (384 dimensions) for semantic search';
