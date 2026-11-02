import pytest

from audit.management.commands.consume_events import Command
from audit.models import AuditEvent, IngestedMessageId


@pytest.mark.django_db
def test_idempotent_event_ingestion(tenant_a):
    cmd = Command()
    msg_id = "msg_uuid_12345"
    IngestedMessageId.objects.create(message_id=msg_id, event_type="vendor.assessment.submitted")

    assert IngestedMessageId.objects.filter(message_id=msg_id).exists()
    assert AuditEvent.objects.count() == 0