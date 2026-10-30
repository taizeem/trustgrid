use axum::http::HeaderMap;
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::error::ServiceError;

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub tid: Option<String>,
    pub email: Option<String>,
}

#[derive(Debug, Clone)]
pub struct AuthContext {
    pub user_id: Uuid,
    pub tenant_id: Uuid,
}

pub fn extract_auth(headers: &HeaderMap) -> Result<AuthContext, ServiceError> {
    let auth_header = headers
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .ok_or_else(|| ServiceError::Unauthorized("Missing Authorization header".into()))?;

    if !auth_header.starts_with("Bearer ") {
        return Err(ServiceError::Unauthorized("Invalid token format".into()));
    }

    let token_str = &auth_header[7..];
    let secret = std::env::var("JWT_SECRET_KEY")
        .unwrap_or_else(|_| "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123".into());

    let mut validation = Validation::new(Algorithm::HS256);
    validation.set_audience(&["trustgrid-services"]);

    let token_data = decode::<Claims>(
        token_str,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation,
    )
    .map_err(|e| ServiceError::Unauthorized(format!("Token verification failed: {}", e)))?;

    let tenant_str = token_data
        .claims
        .tid
        .ok_or_else(|| ServiceError::Unauthorized("Token missing 'tid' claim".into()))?;

    let tenant_id = Uuid::parse_str(&tenant_str)
        .map_err(|_| ServiceError::Unauthorized("Invalid tenant UUID".into()))?;

    let user_id = Uuid::parse_str(&token_data.claims.sub)
        .map_err(|_| ServiceError::Unauthorized("Invalid user UUID".into()))?;

    Ok(AuthContext { user_id, tenant_id })
}