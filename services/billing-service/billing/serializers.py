from rest_framework import serializers
from billing.models import Plan, PlanEntitlement, Subscription, UsageRecord, Invoice

class PlanEntitlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanEntitlement
        fields = ["id", "feature_key", "feature_type", "quota_limit"]


class PlanSerializer(serializers.ModelSerializer):
    entitlements = PlanEntitlementSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "price_cents",
            "currency",
            "billing_interval",
            "trial_days",
            "is_active",
            "entitlements",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "tenant_id",
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "canceled_at",
            "external_customer_id",
            "is_valid",
        ]

    def get_is_valid(self, obj):
        return obj.is_currently_valid()


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = [
            "id",
            "tenant_id",
            "metric_name",
            "quantity",
            "timestamp",
            "idempotency_key",
        ]


class UsageIngestSerializer(serializers.Serializer):
    metric_name = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField(default=1, min_value=1)
    idempotency_key = serializers.CharField(max_length=128)


class CheckoutSessionRequestSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=64)
    success_url = serializers.URLField(required=False, allow_blank=True)
    cancel_url = serializers.URLField(required=False, allow_blank=True)


class PlanChangeSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=64)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "tenant_id",
            "external_invoice_id",
            "amount_cents",
            "currency",
            "status",
            "hosted_invoice_url",
            "paid_at",
            "created_at",
        ]