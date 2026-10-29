use std::path::{Path, PathBuf};
use tokio::fs;
use uuid::Uuid;

use crate::error::ServiceError;

#[derive(Clone)]
pub struct DiskStorage {
    base_dir: PathBuf,
}

impl DiskStorage {
    pub fn new<P: AsRef<Path>>(base_dir: P) -> Self {
        Self {
            base_dir: base_dir.as_ref().to_path_buf(),
        }
    }

    pub async fn save_document(&self, tenant_id: Uuid, doc_id: Uuid, bytes: &[u8]) -> Result<String, ServiceError> {
        let tenant_folder = self.base_dir.join(tenant_id.to_string());
        fs::create_dir_all(&tenant_folder)
            .await
            .map_err(|e| ServiceError::Storage(format!("Failed to create tenant directory: {}", e)))?;

        let file_path = tenant_folder.join(doc_id.to_string());
        fs::write(&file_path, bytes)
            .await
            .map_err(|e| ServiceError::Storage(format!("Failed to write document bytes: {}", e)))?;

        Ok(file_path.to_string_lossy().to_string())
    }

    pub async fn read_document(&self, storage_path: &str) -> Result<Vec<u8>, ServiceError> {
        fs::read(storage_path)
            .await
            .map_err(|e| ServiceError::Storage(format!("Failed to read document: {}", e)))
    }
}