use proptest::prelude::*;
use risk_service::engine::{
    calculator::RiskCalculator,
    models::{
        BusinessCriticality, Certifications, DataSensitivity, IncidentHistory,
        RiskAssessmentInput, SecurityControls,
    },
};
use uuid::Uuid;

fn sample_input(
    ds: DataSensitivity,
    bc: BusinessCriticality,
    mfa: bool,
    enc: bool,
    irp: bool,
    sla: bool,
    soc2: bool,
    iso: bool,
    b12: u32,
    b24: u32,
) -> RiskAssessmentInput {
    RiskAssessmentInput {
        vendor_id: Uuid::new_v4(),
        data_sensitivity: ds,
        business_criticality: bc,
        security_controls: SecurityControls {
            enforces_mfa: mfa,
            encrypts_at_rest: enc,
            has_incident_response_plan: irp,
            meets_vulnerability_sla: sla,
        },
        certifications: Certifications {
            has_soc2_type2: soc2,
            has_iso27001: iso,
        },
        incident_history: IncidentHistory {
            breach_count_last_12m: b12,
            breach_count_last_24m: b24,
        },
        rule_version: Some("v1.0.0".into()),
    }
}

#[test]
fn test_reproducible_calculation() {
    let input = sample_input(
        DataSensitivity::Confidential,
        BusinessCriticality::Tier2High,
        true,
        true,
        true,
        true,
        true,
        false,
        0,
        0,
    );

    let res1 = RiskCalculator::compute(&input).expect("Calculation 1 must succeed");
    let res2 = RiskCalculator::compute(&input).expect("Calculation 2 must succeed");

    assert_eq!(res1.overall_score, res2.overall_score);
    assert_eq!(res1.risk_tier, res2.risk_tier);
    assert_eq!(res1.factor_breakdown.len(), res2.factor_breakdown.len());
}

#[test]
fn test_compliance_credits_reduce_score() {
    let without_certs = sample_input(
        DataSensitivity::HighlySensitive,
        BusinessCriticality::Tier1Critical,
        true,
        true,
        true,
        true,
        false, // No SOC 2
        false, // No ISO
        0,
        0,
    );
    let with_certs = sample_input(
        DataSensitivity::HighlySensitive,
        BusinessCriticality::Tier1Critical,
        true,
        true,
        true,
        true,
        true,  // Has SOC 2 (-10 pts)
        true,  // Has ISO (-5 pts)
        0,
        0,
    );

    let score_without = RiskCalculator::compute(&without_certs).unwrap().overall_score;
    let score_with = RiskCalculator::compute(&with_certs).unwrap().overall_score;

    assert!(
        score_with < score_without,
        "Certifications must strictly reduce risk score"
    );
    assert_eq!(score_without - score_with, 15.0);
}

#[test]
fn test_unsupported_version_rejected() {
    let mut input = sample_input(
        DataSensitivity::Public,
        BusinessCriticality::Tier4Low,
        true,
        true,
        true,
        true,
        false,
        false,
        0,
        0,
    );
    input.rule_version = Some("v99.0.0".into());

    let result = RiskCalculator::compute(&input);
    assert!(result.is_err(), "Unsupported rule version must return Err");
}

// Property-based testing using proptest (verifies range bounds across 256 generated test vectors)
proptest! {
    #[test]
    fn prop_score_always_within_bounds(
        ds_idx in 0u8..4,
        bc_idx in 0u8..4,
        mfa in any::<bool>(),
        enc in any::<bool>(),
        irp in any::<bool>(),
        sla in any::<bool>(),
        soc2 in any::<bool>(),
        iso in any::<bool>(),
        b12 in 0u32..10,
        b24 in 0u32..10,
    ) {
        let ds = match ds_idx {
            0 => DataSensitivity::Public,
            1 => DataSensitivity::Internal,
            2 => DataSensitivity::Confidential,
            _ => DataSensitivity::HighlySensitive,
        };
        let bc = match bc_idx {
            0 => BusinessCriticality::Tier4Low,
            1 => BusinessCriticality::Tier3Medium,
            2 => BusinessCriticality::Tier2High,
            _ => BusinessCriticality::Tier1Critical,
        };

        let input = sample_input(ds, bc, mfa, enc, irp, sla, soc2, iso, b12, b24);
        let res = RiskCalculator::compute(&input).unwrap();

        prop_assert!(res.overall_score >= 0.0);
        prop_assert!(res.overall_score <= 100.0);
    }
}