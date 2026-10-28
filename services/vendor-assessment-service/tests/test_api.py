import uuid
import pytest
from rest_framework import status
from vendors.models import AssessmentSubmissionStatus

@pytest.mark.django_db
def test_vendor_lifecycle_api_flow(api_client, auth_headers, tenant_a):
    headers = auth_headers(tenant_id=tenant_a)

    # 1. Create Vendor
    payload = {
        "name": "Okta",
        "website": "https://okta.com",
        "tier": "tier_1",
        "primary_contact_name": "Security Team",
        "primary_contact_email": "security@okta.com",
    }
    create_resp = api_client.post("/api/v1/vendors/", payload, format="json", **headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    vendor_id = create_resp.data["id"]

    # 2. Create Assessment Template
    template_payload = {
        "title": "Cloud Security Standard",
        "version": 1,
        "schema": {
            "questions": [
                {"id": "q1", "text": "Is MFA enforced for all employees?", "type": "boolean"},
                {"id": "q2", "text": "Data retention period in days", "type": "number"}
            ]
        }
    }
    tmpl_resp = api_client.post("/api/v1/templates/", template_payload, format="json", **headers)
    assert tmpl_resp.status_code == status.HTTP_201_CREATED
    template_id = tmpl_resp.data["id"]

    # 3. Create Draft Submission
    sub_payload = {
        "vendor": vendor_id,
        "template": template_id,
        "answers": {"q1": True, "q2": 90}
    }
    sub_resp = api_client.post("/api/v1/assessments/", sub_payload, format="json", **headers)
    assert sub_resp.status_code == status.HTTP_201_CREATED
    submission_id = sub_resp.data["id"]
    assert sub_resp.data["status"] == AssessmentSubmissionStatus.DRAFT

    # 4. Submit Assessment
    submit_resp = api_client.post(f"/api/v1/assessments/{submission_id}/submit/", **headers)
    assert submit_resp.status_code == status.HTTP_200_OK
    assert submit_resp.data["status"] == AssessmentSubmissionStatus.SUBMITTED
    assert submit_resp.data["submitted_at"] is not None