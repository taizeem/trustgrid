import hashlib
import hmac
import json
import time
import pytest
from django.conf import settings
from billing.models import Subscription, PaymentWebhookEvent, Invoice
from billing.services.payment_provider import StripeSandboxAdapter
from billing.services.entitlements import EntitlementService

def generate_stripe_sig(payload_bytes, secret):
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"

@pytest.mark.django_db
def test_webhook_signature_verification_failure():
    payload = b'{"id": "evt_test", "type": "ping"}'
    invalid_sig = "t=123,v1=bad_signature"
    assert StripeSandboxAdapter.verify_webhook_signature(payload, invalid_sig) is False

@pytest.mark.django_db
def test_webhook_subscription_updated_idempotency(tenant_a, seed_plans):
    sub = EntitlementService.get_or_create_default_subscription(tenant_a)
    sub.external_customer_id = "cus_tenant_a_123"
    sub.save()

    event_id = "evt_sub_upgrade_999"
    payload = {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_ext_456",
                "customer": "cus_tenant_a_123",
                "status": "active",
                "current_period_end": int(time.time()) + 2592000,
                "metadata": {
                    "tenant_id": str(tenant_a),
                    "plan_code": "growth",
                }
            }
        }
    }

    res1 = StripeSandboxAdapter.process_incoming_webhook(event_id, "customer.subscription.updated", payload)
    assert res1["status"] == "processed"

    sub.refresh_from_db()
    assert sub.plan.code == "growth"
    assert sub.status == "active"

    # Duplicate delivery
    res2 = StripeSandboxAdapter.process_incoming_webhook(event_id, "customer.subscription.updated", payload)
    assert res2["status"] == "already_processed"
    assert PaymentWebhookEvent.objects.filter(event_id=event_id).count() == 1