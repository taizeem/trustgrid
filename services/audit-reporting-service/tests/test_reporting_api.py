import pytest
from django.urls import reverse

from audit.models import AuditEvent, AuditSeverity


@pytest.mark.django_db
def test_compliance_readiness_report(api_client, auth_headers, tenant_a):
    headers = auth_headers(tenant_id=tenant_a, roles=["auditor"])

    # Seed events
    AuditEvent.objects.create(
        organization_id=tenant_a,
        action="vendor.onboarded",
        resource_type="vendor",
        resource_id="v_1",
        severity=AuditSeverity.INFO,
    )
    AuditEvent.objects.create(
        organization_id=tenant_a,
        action="security.policy_violation",
        resource_type="policy",
        resource_id="pol_1",
        severity=AuditSeverity.WARNING,
    )

    response = api_client.get(reverse("report-compliance-readiness"), **headers)
    assert response.status_code == 200
    data = response.data
    assert data["total_audit_events"] == 2
    assert data["warning_events"] == 1
    assert data["readiness_score"] == 98


@pytest.mark.django_db
def test_audit_export_csv(api_client, auth_headers, tenant_a):
    headers = auth_headers(tenant_id=tenant_a, roles=["admin"])
    AuditEvent.objects.create(
        organization_id=tenant_a,
        action="assessment.approved",
        resource_type="assessment",
        resource_id="as_888",
    )

    response = api_client.get(reverse("report-audit-export"), **headers)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    content = response.content.decode("utf-8")
    assert "assessment.approved" in content
    assert "as_888" in content