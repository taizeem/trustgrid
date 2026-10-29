use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::UUID;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct DocumentMetadata {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub file_name: String,
    pub content_type: String,
    pub file_size_bytes: i64,
    pub sha256_hash: String,
    pub storage_path: String,
    pub uploaded_by: Uuid,
    pub status: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct DocumentUploadResponse {
    pub id: Uuid,
    pub file_name: String,
    pub content_type: String,
    pub file_size_bytes: i64,
    pub sha256_hash: String,
    pub status: String,
}