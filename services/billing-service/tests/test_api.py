import json
import pytest
from django.urls import reverse
from django.conf import settings
from tests.test_webhooks import generate_stripe_sig

@pytest.mark.django_db
def test_health_check_endpoint(api_client):
    response = api_client.get(reverse("health-check"))
    assert response.status_code == 200
    assert response.data["status"] == "healthy"
    assert response.data["service"] == "billing-service"


@pytest.mark.django_db
def test_plans_list_public(api_client, seed_plans):
    response = api_client.get(reverse("billing-plans"))
    assert response.status_code == 200
    assert len(response.data) == 3
    codes = [p["code"] for p in response.data]
    assert "free" in codes
    assert "growth" in codes
    assert "enterprise" in codes


@pytest.mark.django_db
def test_subscription_unauthenticated_rejected(api_client):
    response = api_client.get(reverse("billing-subscription"))
    assert response.status_code in [401, 403]


@pytest.mark.django_db
def test_plan_change_role_enforcement(api_client, auth_headers, tenant_a, seed_plans):
    # Non-admin (analyst) rejected
    headers_analyst = auth_headers(tenant_id=tenant_a, roles=["analyst"])
    resp_forbidden = api_client.post(
        reverse("billing-change-plan"),
        {"plan_code": "growth"},
        format="json",
        **headers_analyst
    )
    assert resp_forbidden.status_code == 403

    # Admin accepted
    headers_admin = auth_headers(tenant_id=tenant_a, roles=["admin"])
    resp_ok = api_client.post(
        reverse("billing-change-plan"),
        {"plan_code": "growth"},
        format="json",
        **headers_admin
    )
    assert resp_ok.status_code == 200
    assert resp_ok.data["plan"]["code"] == "growth"
    assert resp_ok.data["status"] == "active"


@pytest.mark.django_db
def test_entitlement_check_api(api_client, auth_headers, tenant_a, seed_plans):
    headers = auth_headers(tenant_id=tenant_a)

    # Free plan has 5 max_vendors
    resp = api_client.get(reverse("billing-entitlement-check") + "?feature=max_vendors&quantity=1", **headers)
    assert resp.status_code == 200
    assert resp.data["allowed"] is True
    assert resp.data["remaining"] == 5

    # Requesting 10 vendors on free tier is rejected with 403 Forbidden
    resp_over = api_client.get(reverse("billing-entitlement-check") + "?feature=max_vendors&quantity=10", **headers)
    assert resp_over.status_code == 403
    assert resp_over.data["allowed"] is False


@pytest.mark.django_db
def test_usage_ingest_and_summary_api(api_client, auth_headers, tenant_a, seed_plans):
    headers = auth_headers(tenant_id=tenant_a)

    payload = {
        "metric_name": "max_vendors",
        "quantity": 2,
        "idempotency_key": "api_tx_101",
    }
    resp1 = api_client.post(reverse("billing-usage-ingest"), payload, format="json", **headers)
    assert resp1.status_code == 201
    assert resp1.data["created"] is True

    # Duplicate call returns 200 with idempotent_duplicate
    resp2 = api_client.post(reverse("billing-usage-ingest"), payload, format="json", **headers)
    assert resp2.status_code == 200
    assert resp2.data["created"] is False
    assert resp2.data["status"] == "idempotent_duplicate"

    # Check Summary
    summary_resp = api_client.get(reverse("billing-usage-summary"), **headers)
    assert summary_resp.status_code == 200
    metrics = {m["feature_key"]: m for m in summary_resp.data["metrics"]}
    assert metrics["max_vendors"]["current_usage"] == 2
    assert metrics["max_vendors"]["remaining"] == 3


@pytest.mark.django_db
def test_checkout_session_creation(api_client, auth_headers, tenant_a, seed_plans):
    headers = auth_headers(tenant_id=tenant_a, roles=["admin"])
    payload = {
        "plan_code": "growth",
        "success_url": "https://app.trustgrid.internal/success",
        "cancel_url": "https://app.trustgrid.internal/cancel",
    }
    resp = api_client.post(reverse("billing-checkout-session"), payload, format="json", **headers)
    assert resp.status_code == 201
    assert "session_id" in resp.data
    assert "url" in resp.data
    assert resp.data["amount_cents"] == 49900


@pytest.mark.django_db
def test_stripe_webhook_http_endpoint(api_client, tenant_a, seed_plans):
    event_payload = {
        "id": "evt_http_webhook_001",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_http_99",
                "customer": "cus_tenant_http_1",
                "status": "active",
                "metadata": {
                    "tenant_id": str(tenant_a),
                    "plan_code": "enterprise"
                }
            }
        }
    }
    payload_bytes = json.dumps(event_payload).encode("utf-8")
    sig = generate_stripe_sig(payload_bytes, settings.STRIPE_WEBHOOK_SECRET)

    resp = api_client.post(
        reverse("billing-stripe-webhook"),
        data=payload_bytes,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=sig
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "processed"