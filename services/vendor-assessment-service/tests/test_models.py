import uuid
import pytest
from django.db import IntegrityError
from vendors.models import Vendor, AssessmentTemplate, VendorTier, VendorLifecycleState

@pytest.mark.django_db
def test_create_vendor_defaults(tenant_a):
    user_id = uuid.uuid4()
    vendor = Vendor.objects.create(
        tenant_id=tenant_a,
        name="Cloudflare",
        website="https://cloudflare.com",
        created_by_id=user_id,
    )
    assert vendor.tier == VendorTier.TIER_3
    assert vendor.lifecycle_state == VendorLifecycleState.PROSPECTIVE
    assert vendor.created_at is not None

@pytest.mark.django_db
def test_template_version_uniqueness_per_tenant(tenant_a):
    user_id = uuid.uuid4()
    AssessmentTemplate.objects.create(
        tenant_id=tenant_a,
        title="SOC 2 Assessment",
        version=1,
        schema={"questions": []},
        created_by_id=user_id,
    )
    with pytest.raises(IntegrityError):
        AssessmentTemplate.objects.create(
            tenant_id=tenant_a,
            title="SOC 2 Assessment",
            version=1,
            schema={"questions": []},
            created_by_id=user_id,
        )