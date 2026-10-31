import hashlib
import hmac
import importlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone as dt_tz
from django.conf import settings
from django.utils import timezone
from billing.models import Plan, Subscription, PaymentWebhookEvent, Invoice

logger = logging.getLogger(__name__)

class StripeSandboxAdapter:
    """
    Payment provider integration adapter.
    Supports both real Stripe test-mode API and self-contained sandbox simulation.
    Never stores sensitive raw card information (PAN, CVV).
    """

    @classmethod
    def create_checkout_session(cls, tenant_id, plan_code, success_url=None, cancel_url=None):
        plan = Plan.objects.get(code=plan_code, is_active=True)
        sub = Subscription.objects.filter(tenant_id=tenant_id).first()
        customer_id = sub.external_customer_id if sub and sub.external_customer_id else f"cus_sandbox_{uuid.uuid4().hex[:12]}"

        # Dynamically import stripe only if live test mode is requested, avoiding IDE unresolved warnings
        if not settings.PAYMENT_SANDBOX_MODE and settings.STRIPE_SECRET_KEY.startswith("sk_"):
            try:
                stripe = importlib.import_module("stripe")
                stripe.api_key = settings.STRIPE_SECRET_KEY
                session = stripe.checkout.Session.create(
                    customer=customer_id,
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": plan.currency.lower(),
                            "product_data": {"name": f"TrustGrid {plan.name}"},
                            "unit_amount": plan.price_cents,
                            "recurring": {"interval": plan.billing_interval},
                        },
                        "quantity": 1,
                    }],
                    mode="subscription",
                    success_url=success_url or "https://app.trustgrid.internal/billing/success",
                    cancel_url=cancel_url or "https://app.trustgrid.internal/billing/cancel",
                    client_reference_id=str(tenant_id),
                )
                return {
                    "session_id": session.id,
                    "url": session.url,
                    "customer_id": customer_id,
                    "provider": "stripe_live_test",
                }
            except Exception as e:
                logger.error(f"Stripe API checkout session creation failed: {e}")

        # Deterministic Sandbox Simulation for local development & testing
        session_id = f"cs_test_sandbox_{uuid.uuid4().hex[:16]}"
        checkout_url = f"https://checkout.stripe.com/pay/{session_id}"

        if sub and not sub.external_customer_id:
            sub.external_customer_id = customer_id
            sub.save(update_fields=["external_customer_id"])

        return {
            "session_id": session_id,
            "url": checkout_url,
            "customer_id": customer_id,
            "provider": "stripe_sandbox",
            "plan_code": plan.code,
            "amount_cents": plan.price_cents,
        }

    @classmethod
    def verify_webhook_signature(cls, payload_bytes, sig_header):
        """
        Validates the Stripe webhook HMAC signature against STRIPE_WEBHOOK_SECRET.
        Expected format: 't=1492774577,v1=5257a869e7ecebeda32affa62cd492304fdc3b4bcdc6efde2410f4216e702fb9'
        """
        if not sig_header or not settings.STRIPE_WEBHOOK_SECRET:
            return False

        try:
            pairs = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = pairs.get("t")
            v1_signature = pairs.get("v1")

            if not timestamp or not v1_signature:
                computed = hmac.new(
                    settings.STRIPE_WEBHOOK_SECRET.encode("utf-8"),
                    payload_bytes,
                    hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(computed, sig_header.strip())

            signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
            expected_sig = hmac.new(
                settings.STRIPE_WEBHOOK_SECRET.encode("utf-8"),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_sig, v1_signature)
        except Exception as e:
            logger.warning(f"Webhook signature verification failed with error: {e}")
            return False

    @classmethod
    def process_incoming_webhook(cls, event_id, event_type, payload):
        """
        Processes incoming payment webhook idempotently.
        Deduplicates via PaymentWebhookEvent.event_id.
        """
        event_record, created = PaymentWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "provider": "stripe_sandbox",
                "event_type": event_type,
                "payload": payload,
                "status": "pending",
            }
        )

        if not created and event_record.status == "processed":
            logger.info(f"Duplicate webhook {event_id} already processed. Skipping.")
            return {"status": "already_processed", "event_id": event_id}

        try:
            data_object = payload.get("data", {}).get("object", {})

            if event_type in ["customer.subscription.created", "customer.subscription.updated"]:
                cls._handle_subscription_sync(data_object)

            elif event_type == "customer.subscription.deleted":
                cls._handle_subscription_canceled(data_object)

            elif event_type == "invoice.payment_succeeded":
                cls._handle_invoice_paid(data_object)

            elif event_type == "invoice.payment_failed":
                cls._handle_invoice_failed(data_object)

            else:
                logger.info(f"Ignored unhandled billing webhook event: {event_type}")
                event_record.status = "ignored"
                event_record.save(update_fields=["status"])
                return {"status": "ignored", "event_id": event_id}

            event_record.status = "processed"
            event_record.processed_at = timezone.now()
            event_record.save(update_fields=["status", "processed_at"])
            return {"status": "processed", "event_id": event_id}

        except Exception as exc:
            logger.exception(f"Error processing webhook event {event_id}: {exc}")
            event_record.status = "failed"
            event_record.error_message = str(exc)
            event_record.save(update_fields=["status", "error_message"])
            raise exc

    @classmethod
    def _handle_subscription_sync(cls, data_obj):
        customer_id = data_obj.get("customer")
        ext_sub_id = data_obj.get("id")
        status = data_obj.get("status", "active")
        plan_code = data_obj.get("metadata", {}).get("plan_code") or "growth"
        tenant_id_str = data_obj.get("metadata", {}).get("tenant_id")

        plan = Plan.objects.filter(code=plan_code).first() or Plan.objects.first()

        period_end_timestamp = data_obj.get("current_period_end")
        period_end = datetime.fromtimestamp(period_end_timestamp, tz=dt_tz.utc) if period_end_timestamp else timezone.now() + timezone.timedelta(days=30)

        sub = None
        if tenant_id_str:
            try:
                sub = Subscription.objects.filter(tenant_id=uuid.UUID(tenant_id_str)).first()
            except ValueError:
                pass

        if not sub and customer_id:
            sub = Subscription.objects.filter(external_customer_id=customer_id).first()

        if sub:
            sub.plan = plan
            sub.status = status if status in ["active", "trialing", "past_due", "canceled"] else "active"
            sub.current_period_end = period_end
            sub.external_subscription_id = ext_sub_id
            sub.external_customer_id = customer_id
            sub.save()
            logger.info(f"Updated subscription for tenant {sub.tenant_id} to {plan.code} [{sub.status}]")

    @classmethod
    def _handle_subscription_canceled(cls, data_obj):
        ext_sub_id = data_obj.get("id")
        customer_id = data_obj.get("customer")

        sub = Subscription.objects.filter(external_subscription_id=ext_sub_id).first()
        if not sub and customer_id:
            sub = Subscription.objects.filter(external_customer_id=customer_id).first()

        if sub:
            sub.status = "canceled"
            sub.canceled_at = timezone.now()
            sub.save(update_fields=["status", "canceled_at"])
            logger.info(f"Canceled subscription for tenant {sub.tenant_id}")

    @classmethod
    def _handle_invoice_paid(cls, data_obj):
        inv_id = data_obj.get("id")
        amount = data_obj.get("amount_paid", 0)
        customer_id = data_obj.get("customer")
        hosted_url = data_obj.get("hosted_invoice_url", "")

        sub = Subscription.objects.filter(external_customer_id=customer_id).first()
        if sub and sub.status in ["past_due", "incomplete"]:
            sub.status = "active"
            sub.save(update_fields=["status"])

        tenant_id = sub.tenant_id if sub else uuid.uuid4()
        Invoice.objects.update_or_create(
            external_invoice_id=inv_id,
            defaults={
                "tenant_id": tenant_id,
                "subscription": sub,
                "amount_cents": amount,
                "currency": data_obj.get("currency", "usd").upper(),
                "status": "paid",
                "hosted_invoice_url": hosted_url,
                "paid_at": timezone.now(),
            }
        )
        logger.info(f"Processed invoice.payment_succeeded for invoice {inv_id}")

    @classmethod
    def _handle_invoice_failed(cls, data_obj):
        inv_id = data_obj.get("id")
        customer_id = data_obj.get("customer")
        sub = Subscription.objects.filter(external_customer_id=customer_id).first()

        if sub:
            sub.status = "past_due"
            sub.save(update_fields=["status"])

        tenant_id = sub.tenant_id if sub else uuid.uuid4()
        Invoice.objects.update_or_create(
            external_invoice_id=inv_id,
            defaults={
                "tenant_id": tenant_id,
                "subscription": sub,
                "amount_cents": data_obj.get("amount_due", 0),
                "currency": data_obj.get("currency", "usd").upper(),
                "status": "open",
            }
        )
        logger.warning(f"Processed invoice.payment_failed for invoice {inv_id}, subscription marked past_due")