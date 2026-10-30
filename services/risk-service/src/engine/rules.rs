use super::models::RuleVersionMetadata;

pub const CURRENT_RULE_VERSION: &str = "v1.0.0";

pub fn get_available_rules() -> Vec<RuleVersionMetadata> {
    return vec![
        RuleVersionMetadata {
            version: "v1.0.0".into(),
            name: "TrustGrid Standard Vendor Risk Model v1".into(),
            status: "ACTIVE".into(),
            description: "Weighted evaluation across Data Sensitivity (30%), Criticality (25%), Security Controls (30%), and Incident History (15%) with Certification Mitigations.".into(),
            max_score: 100.0,
            min_score: 0.0,
        }
    ];
}

pub fn get_rule_metadata(version: &str) -> Option<RuleVersionMetadata> {
    return get_available_rules().into_iter().find(|r| r.version == version);
}