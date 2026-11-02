import pytest
from django.urls import reverse

from audit.models import AuditEvent


@pytest.mark.django_db
def test_health_check_endpoint(api_client):
    response = api_client.get(reverse("health-check"))
    assert response.status_code == 200
    assert response.data["status"] == "healthy"
    assert response.data["service"] == "audit-reporting-service"


@pytest.mark.django_db
def test_audit_events_unauthenticated(api_client):
    response = api_client.get(reverse("audit-events-list"))
    assert response.status_code in [401, 403]


@pytest.mark.django_db
def test_audit_events_tenant_isolation(api_client, auth_headers, tenant_a, tenant_b):
    # Create event for Tenant A
    AuditEvent.objects.create(
        organization_id=tenant_a,
        action="assessment.submitted",
        resource_type="assessment",
        resource_id="as_111",
        description="Tenant A event",
    )
    # Create event for Tenant B
    AuditEvent.objects.create(
        organization_id=tenant_b,
        action="assessment.submitted",
        resource_type="assessment",
        resource_id="as_222",
        description="Tenant B event",
    )

    headers_a = auth_headers(tenant_id=tenant_a, roles=["admin"])
    response = api_client.get(reverse("audit-events-list"), **headers_a)
    assert response.status_code == 200
    results = response.data["results"]
    assert len(results) == 1
    assert results[0]["resource_id"] == "as_111"


@pytest.mark.django_db
def test_ingest_audit_event_sync(api_client, auth_headers, tenant_a):
    headers = auth_headers(tenant_id=tenant_a, roles=["admin"])
    payload = {
        "action": "user.login_failed",
        "resource_type": "user",
        "resource_id": "u_999",
        "severity": "WARNING",
        "description": "Failed password attempt",
        "metadata": {"attempt_count": 3},
    }
    response = api_client.post(reverse("audit-events-ingest"), payload, format="json", **headers)
    assert response.status_code == 201
    assert response.data["action"] == "user.login_failed"
    assert response.data["severity"] == "WARNING"
    assert AuditEvent.objects.filter(organization_id=tenant_a, action="user.login_failed").exists()