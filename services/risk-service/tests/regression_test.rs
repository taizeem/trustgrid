use risk_service::engine::{
    calculator::RiskCalculator,
    models::{
        BusinessCriticality, Certifications, DataSensitivity, IncidentHistory,
        RiskAssessmentInput, RiskTier, SecurityControls,
    },
};
use uuid::Uuid;

#[test]
fn test_golden_minimal_risk_vendor() {
    let input = RiskAssessmentInput {
        vendor_id: Uuid::new_v4(),
        data_sensitivity: DataSensitivity::Public,
        business_criticality: BusinessCriticality::Tier4Low,
        security_controls: SecurityControls {
            enforces_mfa: true,
            encrypts_at_rest: true,
            has_incident_response_plan: true,
            meets_vulnerability_sla: true,
        },
        certifications: Certifications {
            has_soc2_type2: true,
            has_iso27001: true,
        },
        incident_history: IncidentHistory {
            breach_count_last_12m: 0,
            breach_count_last_24m: 0,
        },
        rule_version: Some("v1.0.0".into()),
    };

    let result = RiskCalculator::compute(&input).unwrap();
    // 0 (Public) + 5 (Tier4) - 10 (SOC2) - 5 (ISO) = -10.0 -> clamped to 0.0
    assert_eq!(result.overall_score, 0.0);
    assert_eq!(result.risk_tier, RiskTier::Low);
}

#[test]
fn test_golden_standard_saas_vendor() {
    let input = RiskAssessmentInput {
        vendor_id: Uuid::new_v4(),
        data_sensitivity: DataSensitivity::Internal,
        business_criticality: BusinessCriticality::Tier3Medium,
        security_controls: SecurityControls {
            enforces_mfa: true,
            encrypts_at_rest: true,
            has_incident_response_plan: true,
            meets_vulnerability_sla: true,
        },
        certifications: Certifications {
            has_soc2_type2: true,
            has_iso27001: false,
        },
        incident_history: IncidentHistory {
            breach_count_last_12m: 0,
            breach_count_last_24m: 0,
        },
        rule_version: Some("v1.0.0".into()),
    };

    let result = RiskCalculator::compute(&input).unwrap();
    // 10 (Internal) + 10 (Tier3) - 10 (SOC2) = 10.0
    assert_eq!(result.overall_score, 10.0);
    assert_eq!(result.risk_tier, RiskTier::Low);
}

#[test]
fn test_golden_critical_breached_vendor() {
    let input = RiskAssessmentInput {
        vendor_id: Uuid::new_v4(),
        data_sensitivity: DataSensitivity::HighlySensitive,
        business_criticality: BusinessCriticality::Tier1Critical,
        security_controls: SecurityControls {
            enforces_mfa: false,
            encrypts_at_rest: false,
            has_incident_response_plan: false,
            meets_vulnerability_sla: false,
        },
        certifications: Certifications {
            has_soc2_type2: false,
            has_iso27001: false,
        },
        incident_history: IncidentHistory {
            breach_count_last_12m: 1,
            breach_count_last_24m: 1,
        },
        rule_version: Some("v1.0.0".into()),
    };

    let result = RiskCalculator::compute(&input).unwrap();
    // 30 (HighlySensitive) + 25 (Tier1) + 10 (no MFA) + 10 (no enc) + 5 (no IRP) + 5 (SLA fail) + 15 (breach) = 100.0
    assert_eq!(result.overall_score, 100.0);
    assert_eq!(result.risk_tier, RiskTier::Critical);
}