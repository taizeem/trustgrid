import uuid
import time
import httpx
import pytest

@pytest.mark.integration
def test_full_platform_lifecycle(gateway_url, make_tenant_token):
    client = httpx.Client(base_url=gateway_url, timeout=15.0)

    # 1. Identity: Register user and acquire token
    token, tenant_id, user_id = make_tenant_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Billing: Verify entitlement quota for vendors
    ent_resp = client.get(
        "/api/v1/billing/entitlements/check/?feature=max_vendors&quantity=1",
        headers=headers,
    )
    assert ent_resp.status_code == 200
    assert ent_resp.json()["allowed"] is True

    # 3. Vendor: Create Vendor Profile
    vendor_payload = {
        "name": f"Cloudflare Edge {uuid.uuid4().hex[:6]}",
        "website": "https://cloudflare.com",
    }
    v_resp = client.post("/api/v1/vendors/", json=vendor_payload, headers=headers)
    assert v_resp.status_code == 201
    vendor_id = v_resp.json()["id"]

    # 4. Assessment Template: Create Template
    tmpl_payload = {
        "title": "SOC 2 Security Baseline",
        "version": 1,
        "schema": {
            "questions": [
                {"id": "q1", "text": "Do you enforce MFA?", "weight": 40},
                {"id": "q2", "text": "Are audit logs encrypted?", "weight": 60},
            ]
        },
    }
    t_resp = client.post("/api/v1/templates/", json=tmpl_payload, headers=headers)
    assert t_resp.status_code == 201
    template_id = t_resp.json()["id"]

    # 5. Assessment: Create Draft Assessment
    as_payload = {
        "vendor": vendor_id,
        "template": template_id,
        "answers": {"q1": "compliant", "q2": "compliant"},
    }
    a_resp = client.post("/api/v1/assessments/", json=as_payload, headers=headers)
    assert a_resp.status_code == 201
    assessment_id = a_resp.json()["id"]

    # 6. Assessment: Submit (Triggers Transactional Outbox)
    sub_resp = client.post(f"/api/v1/assessments/{assessment_id}/submit/", headers=headers)
    assert sub_resp.status_code == 200
    assert sub_resp.json()["status"] == "SUBMITTED"

    # 7. Risk Service: Compute Deterministic Risk Score
    risk_payload = {
        "assessment_id": assessment_id,
        "answers": [
            {"factor": "mfa", "score": 90.0, "weight": 0.4},
            {"factor": "encryption", "score": 95.0, "weight": 0.6},
        ],
    }
    risk_resp = client.post("/api/v1/risk/calculate/", json=risk_payload, headers=headers)
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert risk_data["overall_score"] == 93.0
    assert risk_data["risk_tier"] == "LOW"

    # 8. Integrations: Register Outbound Webhook
    webhook_payload = {
        "url": "https://httpbin.org/post",
        "events": ["assessment.approved", "workflow.state_changed"],
        "secret": "whsec_test_secret_key_12345",
    }
    wh_resp = client.post("/api/v1/integrations/webhooks/", json=webhook_payload, headers=headers)
    assert wh_resp.status_code in [200, 201]

    # 9. Audit Service: Verify Ingested Audit Trail
    audit_resp = client.get(
        f"/api/v1/audit/events/?resource_id={vendor_id}",
        headers=headers,
    )
    assert audit_resp.status_code == 200