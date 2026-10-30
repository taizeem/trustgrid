use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum DataSensitivity {
    Public,
    Internal,
    Confidential,
    HighlySensitive,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BusinessCriticality {
    #[serde(alias = "TIER_4_LOW")]
    Tier4Low,
    #[serde(alias = "TIER_3_MEDIUM")]
    Tier3Medium,
    #[serde(alias = "TIER_2_HIGH")]
    Tier2High,
    #[serde(alias = "TIER_1_CRITICAL")]
    Tier1Critical,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SecurityControls {
    pub enforces_mfa: bool,
    pub encrypts_at_rest: bool,
    pub has_incident_response_plan: bool,
    pub meets_vulnerability_sla: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Certifications {
    pub has_soc2_type2: bool,
    pub has_iso27001: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IncidentHistory {
    pub breach_count_last_12m: u32,
    pub breach_count_last_24m: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAssessmentInput {
    pub vendor_id: Uuid,
    pub data_sensitivity: DataSensitivity,
    pub business_criticality: BusinessCriticality,
    pub security_controls: SecurityControls,
    pub certifications: Certifications,
    pub incident_history: IncidentHistory,
    pub rule_version: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RiskTier {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FactorContribution {
    pub factor_name: String,
    pub category: String,
    pub points_awarded: f64,
    pub rationale: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskCalculationResult {
    pub vendor_id: Uuid,
    pub rule_version: String,
    pub overall_score: f64,
    pub risk_tier: RiskTier,
    pub factor_breakdown: Vec<FactorContribution>,
    pub disclaimer: String,
    pub calculated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleVersionMetadata {
    pub version: String,
    pub name: String,
    pub status: String,
    pub description: String,
    pub max_score: f64,
    pub min_score: f64,
}