import uuid
from datetime import datetime, timezone
from vendors.models import OutboxEvent, OutboxStatus

def create_outbox_event(tenant_id, event_type, routing_key, data, correlation_id=None):
    """
    Constructs a CloudEvents 1.0 envelope and persists it into the outbox table.
    Must be called within an active transaction.atomic() block.
    """
    event_id = uuid.uuid4()
    envelope = {
        "specversion": "1.0",
        "id": str(event_id),
        "source": "https://service.vendor.trustgrid.internal",
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "tenantid": str(tenant_id),
        "correlationid": str(correlation_id or uuid.uuid4()),
        "data": data,
    }

    return OutboxEvent.objects.create(
        id=event_id,
        tenant_id=tenant_id,
        event_type=event_type,
        routing_key=routing_key,
        payload=envelope,
        status=OutboxStatus.PENDING,
    )