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

@pytest.mark.django_db
def test_subscription_unauthenticated_rejected(api_client):
    response = api_client.get(reverse("billing-subscription"))
    assert response.status_code == 401

@pytest.mark.django_db
def test_plan_change_role_enforcement(api_client, auth_headers, tenant_a, seed_plans):
    headers_analyst = auth_headers(tenant_id=tenant_a, roles=["analyst"])
    resp_forbidden = api_client.post(
        reverse("billing-change-plan"),
        {"plan_code": "growth"},
        format="json",
        **headers_analyst
    )
    assert resp_forbidden.status_code == 403

    headers_admin = auth_headers(tenant_id=tenant_a, roles=["admin"])
    resp_ok = api_client.post(
        reverse("billing-change-plan"),
        {"plan_code": "growth"},
        format="json",
        **headers_admin
    )
    assert resp_ok.status_code == 200
    assert resp_ok.data["plan"]["code"] == "growth"

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

    resp2 = api_client.post(reverse("billing-usage-ingest"), payload, format="json", **headers)
    assert resp2.status_code == 200
    assert resp2.data["status"] == "idempotent_duplicate"