import uuid
from datetime import UTC, datetime

import pytest

REQUIRED_CLOUDEVENTS_KEYS = {
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "tenantid",
    "correlationid",
    "data",
}

def validate_cloudevent_envelope(event_dict):
    """Asserts that a dictionary satisfies CloudEvents 1.0 specification."""
    missing_keys = REQUIRED_CLOUDEVENTS_KEYS - set(event_dict.keys())
    assert not missing_keys, f"CloudEvent envelope missing required fields: {missing_keys}"
    assert event_dict["specversion"] == "1.0"
    assert event_dict["datacontenttype"] == "application/json"
    assert uuid.UUID(event_dict["id"])
    assert uuid.UUID(event_dict["tenantid"])
    assert uuid.UUID(event_dict["correlationid"])

@pytest.mark.contracts
def test_assessment_submitted_event_contract():
    event = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "https://service.vendor.trustgrid.internal",
        "type": "vendor.assessment.submitted",
        "datacontenttype": "application/json",
        "time": datetime.now(UTC).isoformat(),
        "tenantid": str(uuid.uuid4()),
        "correlationid": str(uuid.uuid4()),
        "data": {
            "assessment_id": str(uuid.uuid4()),
            "vendor_id": str(uuid.uuid4()),
            "template_id": str(uuid.uuid4()),
            "submitted_by": "user-123",
        },
    }
    validate_cloudevent_envelope(event)
    assert "assessment_id" in event["data"]
    assert "vendor_id" in event["data"]