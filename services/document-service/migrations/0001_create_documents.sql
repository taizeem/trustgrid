CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    uploaded_by UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents (tenant_id, sha256_hash);