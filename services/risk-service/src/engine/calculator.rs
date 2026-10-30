use chrono::Utc;
use thiserror::Error;

use super::models::{
    BusinessCriticality, DataSensitivity, FactorContribution, RiskAssessmentInput,
    RiskCalculationResult, RiskTier,
};
use super::rules::CURRENT_RULE_VERSION;

#[derive(Error, Debug)]
pub enum RiskEngineError {
    #[error("Unsupported rule version: {0}. Supported versions: {1}")]
    UnsupportedRuleVersion(String, String),
}

pub struct RiskCalculator;

impl RiskCalculator {
    pub const LEGAL_DISCLAIMER: &'static str = 
        "Calculated risk scores are quantitative indicators derived from evaluated criteria and do not constitute legal or regulatory compliance certifications.";

    pub fn compute(input: &RiskAssessmentInput) -> Result<RiskCalculationResult, RiskEngineError> {
        let requested_version = input
            .rule_version
            .as_deref()
            .unwrap_or(CURRENT_RULE_VERSION);

        if requested_version != CURRENT_RULE_VERSION {
            return Err(RiskEngineError::UnsupportedRuleVersion(
                requested_version.to_string(),
                CURRENT_RULE_VERSION.to_string(),
            ));
        }

        let mut breakdown = Vec::new();
        let mut raw_score = 0.0;

        // 1. Data Sensitivity Factor (Max: 30 pts)
        let (ds_pts, ds_rationale) = match input.data_sensitivity {
            DataSensitivity::Public => (0.0, "Publicly available data; negligible exposure impact."),
            DataSensitivity::Internal => (10.0, "Internal operational data; moderate exposure impact."),
            DataSensitivity::Confidential => (20.0, "Confidential proprietary or financial data."),
            DataSensitivity::HighlySensitive => (30.0, "Regulated PII, PHI, or cardholder data requiring strict controls."),
        };
        raw_score += ds_pts;
        breakdown.push(FactorContribution {
            factor_name: "Data Sensitivity".into(),
            category: "DATA_CLASSIFICATION".into(),
            points_awarded: ds_pts,
            rationale: ds_rationale.into(),
        });

        // 2. Business Criticality Factor (Max: 25 pts)
        let (bc_pts, bc_rationale) = match input.business_criticality {
            BusinessCriticality::Tier4Low => (5.0, "Tier 4: Non-essential operational dependency; readily replaceable."),
            BusinessCriticality::Tier3Medium => (10.0, "Tier 3: Moderate operational dependency with manual workarounds."),
            BusinessCriticality::Tier2High => (18.0, "Tier 2: Core workflow dependency; disruption impacts deliverables."),
            BusinessCriticality::Tier1Critical => (25.0, "Tier 1: Mission-critical infrastructure; failure causes severe loss."),
        };
        raw_score += bc_pts;
        breakdown.push(FactorContribution {
            factor_name: "Business Criticality".into(),
            category: "OPERATIONAL_IMPACT".into(),
            points_awarded: bc_pts,
            rationale: bc_rationale.into(),
        });

        // 3. Security Controls - Deficit Additions (Max: 30 pts)
        if !input.security_controls.enforces_mfa {
            raw_score += 10.0;
            breakdown.push(FactorContribution {
                factor_name: "MFA Enforcement Deficit".into(),
                category: "SECURITY_POSTURE".into(),
                points_awarded: 10.0,
                rationale: "Absence of enforced multi-factor authentication increases credential compromise risk.".into(),
            });
        }

        if !input.security_controls.encrypts_at_rest {
            raw_score += 10.0;
            breakdown.push(FactorContribution {
                factor_name: "Encryption at Rest Deficit".into(),
                category: "SECURITY_POSTURE".into(),
                points_awarded: 10.0,
                rationale: "Data at rest is unencrypted, exposing stored assets to exfiltration.".into(),
            });
        }

        if !input.security_controls.has_incident_response_plan {
            raw_score += 5.0;
            breakdown.push(FactorContribution {
                factor_name: "Incident Response Plan Deficit".into(),
                category: "GOVERNANCE".into(),
                points_awarded: 5.0,
                rationale: "No formalized incident response protocol verified.".into(),
            });
        }

        if !input.security_controls.meets_vulnerability_sla {
            raw_score += 5.0;
            breakdown.push(FactorContribution {
                factor_name: "Vulnerability SLA Deficit".into(),
                category: "SECURITY_POSTURE".into(),
                points_awarded: 5.0,
                rationale: "Vendor breaches remediation SLAs for identified security vulnerabilities.".into(),
            });
        }

        // 4. Certification Mitigations - Deductions (Max: -15 pts)
        if input.certifications.has_soc2_type2 {
            raw_score -= 10.0;
            breakdown.push(FactorContribution {
                factor_name: "SOC 2 Type II Credit".into(),
                category: "COMPLIANCE_MITIGATION".into(),
                points_awarded: -10.0,
                rationale: "Verified independent SOC 2 Type II attestation demonstrates operating effectiveness of controls.".into(),
            });
        }

        if input.certifications.has_iso27001 {
            raw_score -= 5.0;
            breakdown.push(FactorContribution {
                factor_name: "ISO 27001 Credit".into(),
                category: "COMPLIANCE_MITIGATION".into(),
                points_awarded: -5.0,
                rationale: "Certified Information Security Management System (ISMS) verified.".into(),
            });
        }

        // 5. Incident History (Max: 15 pts)
        if input.incident_history.breach_count_last_12m > 0 {
            raw_score += 15.0;
            breakdown.push(FactorContribution {
                factor_name: "Recent Security Breach".into(),
                category: "INCIDENT_HISTORY".into(),
                points_awarded: 15.0,
                rationale: format!(
                    "{} confirmed security incident(s) reported in the past 12 months.",
                    input.incident_history.breach_count_last_12m
                ),
            });
        } else if input.incident_history.breach_count_last_24m > 0 {
            raw_score += 8.0;
            breakdown.push(FactorContribution {
                factor_name: "Historical Security Breach".into(),
                category: "INCIDENT_HISTORY".into(),
                points_awarded: 8.0,
                rationale: format!(
                    "{} security incident(s) reported in the past 24 months.",
                    input.incident_history.breach_count_last_24m
                ),
            });
        }

        // 6. Normalization & Clamping to [0.00, 100.00]
        let clamped = raw_score.clamp(0.0, 100.0);
        let final_score = (clamped * 100.0).round() / 100.0;

        let risk_tier = match final_score {
            s if s <= 25.0 => RiskTier::Low,
            s if s <= 50.0 => RiskTier::Medium,
            s if s <= 75.0 => RiskTier::High,
            _ => RiskTier::Critical,
        };

        Ok(RiskCalculationResult {
            vendor_id: input.vendor_id,
            rule_version: requested_version.to_string(),
            overall_score: final_score,
            risk_tier,
            factor_breakdown: breakdown,
            disclaimer: Self::LEGAL_DISCLAIMER.into(),
            calculated_at: Utc::now().to_rfc3339(),
        })
    }
}