import uuid
import pytest
from rest_framework import status
from vendors.models import OutboxEvent, OutboxStatus, Vendor, AssessmentTemplate, AssessmentSubmission

@pytest.mark.django_db
def test_outbox_event_created_on_submission(api_client, auth_headers, tenant_a):
    headers = auth_headers(tenant_id=tenant_a)

    vendor = Vendor.objects.create(tenant_id=tenant_a, name="MongoDB", created_by_id=uuid.uuid4())
    template = AssessmentTemplate.objects.create(
        tenant_id=tenant_a, title="ISO 27001", schema={}, created_by_id=uuid.uuid4()
    )
    submission = AssessmentSubmission.objects.create(
        tenant_id=tenant_a, vendor=vendor, template=template, answers={"q_backup": True}
    )

    # Trigger submit action
    response = api_client.post(
        f"/api/v1/assessments/{submission.id}/submit/",
        HTTP_X_CORRELATION_ID="corr-12345",
        **headers
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify Outbox record was created
    outbox = OutboxEvent.objects.filter(tenant_id=tenant_a).first()
    assert outbox is not None
    assert outbox.status == OutboxStatus.PENDING
    assert outbox.event_type == "com.trustgrid.assessment.submitted.v1"
    assert outbox.routing_key == "vendor.assessment.submitted.v1"
    assert outbox.payload["correlationid"] == "corr-12345"
    assert outbox.payload["data"]["assessment_id"] == str(submission.id)