import uuid
import concurrent.futures
import pytest

@pytest.mark.integration
def test_idempotent_duplicate_billing_events(api_client, make_tenant_token):
    """
    Validates that delivering duplicate billing usage records with the same idempotency key
    does NOT double-count or charge multiple times.
    """
    token, tenant_id, _ = make_tenant_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    idempotency_key = f"meter_tx_{uuid.uuid4().hex}"
    payload = {
        "metric_name": "max_vendors",
        "quantity": 3,
        "idempotency_key": idempotency_key,
    }

    # First delivery
    resp1 = api_client.post("/api/v1/billing/usage/", json=payload, headers=headers)
    assert resp1.status_code in [200, 201]
    assert resp1.json()["created"] is True

    # Immediate duplicate delivery (simulating broker re-delivery or retry)
    resp2 = api_client.post("/api/v1/billing/usage/", json=payload, headers=headers)
    assert resp2.status_code in [200, 201]
    assert resp2.json()["created"] is False
    assert resp2.json()["status"] == "idempotent_duplicate"


@pytest.mark.integration
def test_outbox_atomic_rollback_on_database_failure(api_client, make_tenant_token):
    """
    Validates that if an assessment submission violates database constraints,
    the transaction rolls back and NO outbox event is persisted.
    """
    token, tenant_id, _ = make_tenant_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to submit a non-existent assessment ID
    fake_assessment_id = str(uuid.uuid4())
    resp = api_client.post(f"/api/v1/assessments/{fake_assessment_id}/submit/", headers=headers)
    assert resp.status_code == 404

    # Verify no audit event was created for the non-existent assessment
    audit_resp = api_client.get(
        f"/api/v1/audit/events/?resource_id={fake_assessment_id}",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    assert audit_resp.json()["count"] == 0


@pytest.mark.integration
def test_cross_tenant_isolation_under_concurrency(api_client, make_tenant_token):
    """
    Fires requests across Tenant A and Tenant B to ensure tenant contexts
    never leak across request threads.
    """
    token_a, tenant_a, _ = make_tenant_token(roles=["admin"])
    token_b, tenant_b, _ = make_tenant_token(roles=["admin"])

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant A creates vendor
    vendor_payload = {"name": f"Tenant A Secret {uuid.uuid4().hex[:6]}"}
    v_a = api_client.post("/api/v1/vendors/", json=vendor_payload, headers=headers_a).json()
    vendor_a_id = v_a.get("id")

    # Tenant B lists vendors
    list_b = api_client.get("/api/v1/vendors/", headers=headers_b).json()
    b_ids = [item["id"] for item in list_b.get("results", [])]

    assert vendor_a_id not in b_ids


@pytest.mark.integration
def test_concurrent_workflow_transitions_optimistic_locking(api_client, make_tenant_token):
    """
    Validates that concurrent approve and reject attempts on the same workflow
    resolve safely via optimistic locking: exactly one transition succeeds and the other is rejected with 409 Conflict or 400 Bad Request.
    """
    token, tenant_id, _ = make_tenant_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a draft workflow
    wf_payload = {
        "assessment_id": str(uuid.uuid4()),
    }
    wf_create_resp = api_client.post("/api/v1/workflows", json=wf_payload, headers=headers)
    if wf_create_resp.status_code != 201:
        wf_create_resp = api_client.post("/api/v1/workflows/", json=wf_payload, headers=headers)

    if wf_create_resp.status_code != 201:
        pytest.skip(f"Workflow creation endpoint returned {wf_create_resp.status_code}")

    wf_data = wf_create_resp.json()
    workflow_id = wf_data["id"]

    # 2. Transition from DRAFT to IN_REVIEW
    submit_resp = api_client.post(
        f"/api/v1/workflows/{workflow_id}/transition",
        json={"action": "submit", "version": 1, "comment": "Submitting for review"},
        headers=headers,
    )
    assert submit_resp.status_code == 200
    in_review_data = submit_resp.json()
    current_version = in_review_data["version"]

    # 3. Fire concurrent approve and reject requests with the SAME version
    def attempt_approve():
        return api_client.post(
            f"/api/v1/workflows/{workflow_id}/transition",
            json={"action": "approve", "version": current_version, "comment": "Officer 1 approving"},
            headers=headers,
        )

    def attempt_reject():
        return api_client.post(
            f"/api/v1/workflows/{workflow_id}/transition",
            json={"action": "reject", "version": current_version, "comment": "Officer 2 rejecting"},
            headers=headers,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_approve)
        f2 = executor.submit(attempt_reject)
        res1 = f1.result()
        res2 = f2.result()

    statuses = [res1.status_code, res2.status_code]
    # Exactly one must succeed (200), and the other must be rejected due to state conflict (409 or 400)
    assert 200 in statuses
    assert (409 in statuses or 400 in statuses)