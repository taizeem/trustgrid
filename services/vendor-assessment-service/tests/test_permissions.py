import uuid
import pytest
from rest_framework import status
from vendors.models import Vendor

@pytest.mark.django_db
def test_cross_tenant_vendor_isolation(api_client, auth_headers, tenant_a, tenant_b):
    # Seed vendor in Tenant A
    vendor_a = Vendor.objects.create(
        tenant_id=tenant_a,
        name="Datadog",
        created_by_id=uuid.uuid4(),
    )

    # Tenant B attempts to fetch Tenant A's vendor
    headers_b = auth_headers(tenant_id=tenant_b)
    response = api_client.get(f"/api/v1/vendors/{vendor_a.id}/", **headers_b)

    # Must return 404 NOT FOUND (prevents tenant enumeration)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_request_missing_tenant_id_claim_rejected(api_client, create_jwt):
    # JWT issued without a tenant_id ('tid') claim
    token_no_tid = create_jwt(tenant_id=None)
    response = api_client.get(
        "/api/v1/vendors/",
        HTTP_AUTHORIZATION=f"Bearer {token_no_tid}"
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN