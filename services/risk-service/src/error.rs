use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use thiserror::Error;

use crate::engine::calculator::RiskEngineError;

#[derive(Error, Debug)]
pub enum ServiceError {
    #[error("Unauthorized: {0}")]
    Unauthorized(String),

    #[error("Calculation error: {0}")]
    Calculation(#[from] RiskEngineError),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Rule not found: {0}")]
    RuleNotFound(String),
}

impl IntoResponse for ServiceError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            ServiceError::Unauthorized(msg) => (StatusCode::UNAUTHORIZED, msg.clone()),
            ServiceError::Calculation(err) => (StatusCode::BAD_REQUEST, err.to_string()),
            ServiceError::Validation(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            ServiceError::RuleNotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
        };

        let body = Json(json!({ "error": message }));
        (status, body).into_response()
    }
}