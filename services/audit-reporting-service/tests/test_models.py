import uuid
import pytest
from django.core.exceptions import PermissionDenied
from audit.models import AuditEvent, AuditSeverity

@pytest.mark.django_db
def test_audit_event_creation_and_immutability(tenant_a):
    event = AuditEvent.objects.create(
        organization_id=tenant_a,
        actor_id="user_123",
        actor_email="admin@enterprise.test",
        action="vendor.created",
        resource_type="vendor",
        resource_id="v_456",
        severity=AuditSeverity.INFO,
        description="Vendor created successfully",
        metadata={"vendor_name": "Acme Corp"},
    )
    assert event.id is not None
    assert event.checksum != ""
    assert event.created_at is not None

    # Verify update throws PermissionDenied
    event.action = "vendor.modified"
    with pytest.raises(PermissionDenied):
        event.save()

    # Verify delete throws PermissionDenied
    with pytest.raises(PermissionDenied):
        event.delete()