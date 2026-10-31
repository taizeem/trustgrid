import uuid
import pytest
from django.utils import timezone
from billing.models import Plan, PlanEntitlement, Subscription, UsageRecord, Invoice

@pytest.mark.django_db
def test_plan_and_entitlement_creation():
    plan = Plan.objects.create(
        code="custom_tier",
        name="Custom Tier",
        price_cents=10000,
        currency="USD",
        billing_interval="month",
    )
    ent = PlanEntitlement.objects.create(
        plan=plan,
        feature_key="max_vendors",
        feature_type="quota",
        quota_limit=25
    )
    assert plan.price_cents == 10000
    assert str(plan) == "Custom Tier (custom_tier) - 100.00 USD"
    assert ent.quota_limit == 25
    assert ent.feature_type == "quota"


@pytest.mark.django_db
def test_subscription_validity():
    plan = Plan.objects.create(code="test_plan", name="Test Plan", price_cents=5000)
    tenant_id = uuid.uuid4()
    now = timezone.now()

    sub = Subscription.objects.create(
        tenant_id=tenant_id,
        plan=plan,
        status="active",
        current_period_start=now,
        current_period_end=now + timezone.timedelta(days=30),
    )
    assert sub.is_currently_valid() is True

    # Expired subscription
    sub.current_period_end = now - timezone.timedelta(days=1)
    sub.save()
    assert sub.is_currently_valid() is False


@pytest.mark.django_db
def test_invoice_creation():
    tenant_id = uuid.uuid4()
    inv = Invoice.objects.create(
        tenant_id=tenant_id,
        external_invoice_id="in_test_12345",
        amount_cents=49900,
        currency="USD",
        status="paid",
    )
    assert inv.amount_cents == 49900
    assert inv.status == "paid"