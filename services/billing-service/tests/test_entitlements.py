import pytest
from django.utils import timezone
from billing.models import UsageRecord
from billing.services.entitlements import EntitlementService

@pytest.mark.django_db
def test_default_subscription_auto_provisioning(tenant_a, seed_plans):
    sub = EntitlementService.get_or_create_default_subscription(tenant_a)
    assert sub.tenant_id == tenant_a
    assert sub.plan.code == "free"
    assert sub.status == "trialing"
    assert sub.is_currently_valid() is True


@pytest.mark.django_db
def test_boolean_feature_access(tenant_a, seed_plans):
    # Free tier has 'api_access', but does NOT have 'custom_risk_rules'
    api_check = EntitlementService.check_feature_access(tenant_a, "api_access")
    assert api_check["allowed"] is True

    rule_check = EntitlementService.check_feature_access(tenant_a, "custom_risk_rules")
    assert rule_check["allowed"] is False
    assert "not included" in rule_check["reason"]


@pytest.mark.django_db
def test_quota_feature_access_and_limits(tenant_a, seed_plans):
    check_initial = EntitlementService.check_feature_access(tenant_a, "max_vendors", requested_increment=1)
    assert check_initial["allowed"] is True
    assert check_initial["remaining"] == 5

    # Consume 4 vendors
    UsageRecord.objects.create(
        tenant_id=tenant_a,
        metric_name="max_vendors",
        quantity=4,
        idempotency_key="batch_1"
    )

    check_partial = EntitlementService.check_feature_access(tenant_a, "max_vendors", requested_increment=1)
    assert check_partial["allowed"] is True
    assert check_partial["remaining"] == 1

    # Adding 2 more exceeds limit of 5 (4 + 2 = 6 > 5)
    check_exceeded = EntitlementService.check_feature_access(tenant_a, "max_vendors", requested_increment=2)
    assert check_exceeded["allowed"] is False
    assert "Quota exceeded" in check_exceeded["reason"]


@pytest.mark.django_db
def test_unlimited_quota_on_enterprise(tenant_a, seed_plans):
    sub = EntitlementService.get_or_create_default_subscription(tenant_a)
    sub.plan = seed_plans["enterprise"]
    sub.save()

    check_unlimited = EntitlementService.check_feature_access(tenant_a, "max_vendors", requested_increment=1000)
    assert check_unlimited["allowed"] is True
    assert check_unlimited["quota_limit"] is None