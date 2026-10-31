import pytest
from billing.models import UsageRecord
from billing.services.usage import UsageMeteringService

@pytest.mark.django_db
def test_usage_idempotency_prevents_duplicate_counting(tenant_a, seed_plans):
    idempotency_key = "req_vendor_creation_tx_99812"

    rec1, created1 = UsageMeteringService.record_usage(
        tenant_id=tenant_a,
        metric_name="max_vendors",
        quantity=1,
        idempotency_key=idempotency_key,
    )
    assert created1 is True
    assert rec1.quantity == 1

    rec2, created2 = UsageMeteringService.record_usage(
        tenant_id=tenant_a,
        metric_name="max_vendors",
        quantity=1,
        idempotency_key=idempotency_key,
    )
    assert created2 is False
    assert rec1.id == rec2.id

    count = UsageRecord.objects.filter(tenant_id=tenant_a, metric_name="max_vendors").count()
    assert count == 1