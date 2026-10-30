use axum::{
    extract::{Multipart, Path, State},
    http::{header, HeaderMap, StatusCode},
    response::IntoResponse,
    Json,
};
use sha2::{Digest, Sha256};
use sqlx::PgPool;
use uuid::Uuid;

use crate::{
    auth::extract_auth,
    error::ServiceError,
    models::{DocumentMetadata, DocumentUploadResponse},
    storage::DiskStorage,
    validator::{FileValidator, MAX_FILE_SIZE},
};

#[derive(Clone)]
pub struct AppState {
    pub db: PgPool,
    pub storage: DiskStorage,
}

pub async fn upload_document(
    State(state): State<AppState>,
    headers: HeaderMap,
    mut multipart: Multipart,
) -> Result<(StatusCode, Json<DocumentUploadResponse>), ServiceError> {
    let auth = extract_auth(&headers)?;
    let mut file_bytes = Vec::new();
    let mut file_name = "unnamed".to_string();

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| ServiceError::Validation(format!("Multipart error: {}", e)))?
    {
        if field.name() == Some("file") {
            if let Some(name) = field.file_name() {
                file_name = name.to_string();
            }

            let bytes = field
                .bytes()
                .await
                .map_err(|e| ServiceError::Validation(format!("Failed to read field bytes: {}", e)))?;

            if bytes.len() > MAX_FILE_SIZE {
                return Err(ServiceError::FileTooLarge);
            }
            file_bytes = bytes.to_vec();
            break;
        }
    }

    if file_bytes.is_empty() {
        return Err(ServiceError::Validation("No file field provided in form-data".into()));
    }

    let detected_mime = FileValidator::sniff_mime_type(&file_bytes)?;

    let mut hasher = Sha256::new();
    hasher.update(&file_bytes);
    let sha256_hash = hex::encode(hasher.finalize());

    let doc_id = Uuid::new_v4();
    let storage_path = state.storage.save_document(auth.tenant_id, doc_id, &file_bytes).await?;

    let size_bytes = file_bytes.len() as i64;
    let query = r#"
        INSERT INTO documents (id, tenant_id, file_name, content_type, file_size_bytes, sha256_hash, storage_path, uploaded_by, status, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'COMPLETED', NOW())
    "#;

    sqlx::query(query)
        .bind(doc_id)
        .bind(auth.tenant_id)
        .bind(&file_name)
        .bind(detected_mime)
        .bind(size_bytes)
        .bind(&sha256_hash)
        .bind(&storage_path)
        .bind(auth.user_id)
        .execute(&state.db)
        .await?;

    let response = DocumentUploadResponse {
        id: doc_id,
        file_name,
        content_type: detected_mime.to_string(),
        file_size_bytes: size_bytes,
        sha256_hash,
        status: "COMPLETED".into(),
    };

    Ok((StatusCode::CREATED, Json(response)))
}

pub async fn get_document_metadata(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<Uuid>,
) -> Result<Json<DocumentMetadata>, ServiceError> {
    let auth = extract_auth(&headers)?;
    let query = r#"
        SELECT id, tenant_id, file_name, content_type, file_size_bytes, sha256_hash, storage_path, uploaded_by, status, created_at
        FROM documents
        WHERE id = $1 AND tenant_id = $2
    "#;

    let doc = sqlx::query_as::<_, DocumentMetadata>(query)
        .bind(id)
        .bind(auth.tenant_id)
        .fetch_optional(&state.db)
        .await?
        .ok_or(ServiceError::NotFound)?;

    Ok(Json(doc))
}

pub async fn download_document(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<Uuid>,
) -> Result<impl IntoResponse, ServiceError> {
    let auth = extract_auth(&headers)?;
    let query = "SELECT storage_path, content_type, file_name FROM documents WHERE id = $1 AND tenant_id = $2";
    let row: (String, String, String) = sqlx::query_as::<_, (String, String, String)>(query)
        .bind(id)
        .bind(auth.tenant_id)
        .fetch_optional(&state.db)
        .await?
        .ok_or(ServiceError::NotFound)?;

    let bytes = state.storage.read_document(&row.0).await?;

    let mut headers_map = HeaderMap::new();
    headers_map.insert(header::CONTENT_TYPE, row.1.parse().unwrap());
    headers_map.insert(
        header::CONTENT_DISPOSITION,
        format!("attachment; filename=\"{}\"", row.2).parse().unwrap(),
    );

    Ok((headers_map, bytes))
}