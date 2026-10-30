use axum::{
    extract::Path,
    http::StatusCode,
    Json,
};

use crate::{
    auth::AuthContext,
    engine::{
        calculator::RiskCalculator,
        models::{RiskAssessmentInput, RiskCalculationResult, RuleVersionMetadata},
        rules::{get_available_rules, get_rule_metadata},
    },
    error::ServiceError,
};

pub async fn compute_risk(
    _auth: AuthContext,
    Json(payload): Json<RiskAssessmentInput>,
) -> Result<(StatusCode, Json<RiskCalculationResult>), ServiceError> {
    let result = RiskCalculator::compute(&payload)?;
    Ok((StatusCode::OK, Json(result)))
}

pub async fn list_rules(_auth: AuthContext) -> Json<Vec<RuleVersionMetadata>> {
    Json(get_available_rules())
}

pub async fn get_rule(
    _auth: AuthContext,
    Path(version): Path<String>,
) -> Result<Json<RuleVersionMetadata>, ServiceError> {
    let rule = get_rule_metadata(&version)
        .ok_or_else(|| ServiceError::RuleNotFound(format!("Rule version '{}' not found", version)))?;
    Ok(Json(rule))
}

pub async fn health_check() -> &'static str {
    r#"{"status":"healthy","service":"risk-service"}"#
}