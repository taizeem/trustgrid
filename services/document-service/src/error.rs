use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ServiceError {
    #[error("Unauthorized: {0}")]
    Unauthorized(String),

    #[error("Document not found")]
    NotFound,

    #[error("File validation failed: {0}")]
    Validation(String),

    #[error("Payload exceeds maximum size limit")]
    FileTooLarge,

    #[error("Storage error: {0}")]
    Storage(String),

    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[allow(dead_code)]
    #[error("Internal error: {0}")]
    Internal(String),
}

impl IntoResponse for ServiceError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            ServiceError::Unauthorized(msg) => (StatusCode::FORBIDDEN, msg.clone()),
            ServiceError::NotFound => (StatusCode::NOT_FOUND, self.to_string()),
            ServiceError::Validation(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            ServiceError::FileTooLarge => (StatusCode::PAYLOAD_TOO_LARGE, self.to_string()),
            ServiceError::Storage(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
            ServiceError::Database(err) => (StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", err)),
            ServiceError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
        };

        let body = Json(json!({ "error": message }));
        (status, body).into_response()
    }
}