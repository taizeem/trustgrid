import uuid
from django.db import models
from django.utils import timezone

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    price_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    billing_interval = models.CharField(
        max_length=16,
        choices=[("month", "Monthly"), ("year", "Annual")],
        default="month"
    )
    trial_days = models.IntegerField(default=14)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_plans"
        ordering = ["price_cents"]

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.price_cents / 100:.2f} {self.currency}"


class PlanEntitlement(models.Model):
    FEATURE_TYPES = [
        ("boolean", "Boolean Flag"),
        ("quota", "Numeric Quota"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, related_name="entitlements", on_delete=models.CASCADE)
    feature_key = models.CharField(max_length=64, db_index=True)
    feature_type = models.CharField(max_length=16, choices=FEATURE_TYPES, default="boolean")
    quota_limit = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "billing_plan_entitlements"
        unique_together = ("plan", "feature_key")

    def __str__(self):
        limit_desc = "unlimited" if self.quota_limit is None else str(self.quota_limit)
        return f"{self.plan.code} -> {self.feature_key}: {self.feature_type} ({limit_desc})"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("unpaid", "Unpaid"),
        ("incomplete", "Incomplete"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(unique=True, db_index=True)
    plan = models.ForeignKey(Plan, related_name="subscriptions", on_delete=models.PROTECT)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="trialing", db_index=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    external_customer_id = models.CharField(max_length=128, blank=True, db_index=True)
    external_subscription_id = models.CharField(max_length=128, blank=True, null=True, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscriptions"

    def is_currently_valid(self):
        """Active or trialing subscriptions within valid period."""
        return self.status in ["active", "trialing"] and timezone.now() <= self.current_period_end

    def __str__(self):
        return f"Tenant {self.tenant_id} -> Plan: {self.plan.code} [{self.status}]"


class UsageRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    metric_name = models.CharField(max_length=64, db_index=True)
    quantity = models.IntegerField(default=1)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)
    recorded_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "billing_usage_records"
        indexes = [
            models.Index(fields=["tenant_id", "metric_name", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.tenant_id} - {self.metric_name} +{self.quantity} ({self.idempotency_key})"


class PaymentWebhookEvent(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("ignored", "Ignored"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, default="stripe_sandbox")
    event_id = models.CharField(max_length=128, unique=True, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "billing_webhook_events"

    def __str__(self):
        return f"Webhook[{self.provider}] {self.event_type} ({self.event_id}) [{self.status}]"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("paid", "Paid"),
        ("uncollectible", "Uncollectible"),
        ("void", "Void"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    subscription = models.ForeignKey(
        Subscription,
        related_name="invoices",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    external_invoice_id = models.CharField(max_length=128, unique=True, null=True, blank=True, db_index=True)
    amount_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="open", db_index=True)
    hosted_invoice_url = models.URLField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_invoices"

    def __str__(self):
        return f"Invoice {self.external_invoice_id or self.id} - {self.amount_cents / 100:.2f} {self.currency} [{self.status}]"