import logging
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.utils import timezone
from billing.models import UsageRecord, PlanEntitlement
from billing.services.entitlements import EntitlementService

logger = logging.getLogger(__name__)

class UsageMeteringService:
    @staticmethod
    def record_usage(tenant_id, metric_name, quantity=1, idempotency_key=None, recorded_by=None):
        """
        Records metric consumption for a tenant idempotently.
        If idempotency_key has already been processed, returns the existing record without incrementing.
        """
        if not idempotency_key:
            raise ValueError("idempotency_key is required for usage metering.")

        # Ensure default subscription is provisioned before usage record is stamped
        EntitlementService.get_or_create_default_subscription(tenant_id)

        try:
            with transaction.atomic():
                record, created = UsageRecord.objects.get_or_create(
                    idempotency_key=idempotency_key,
                    defaults={
                        "tenant_id": tenant_id,
                        "metric_name": metric_name,
                        "quantity": quantity,
                        "timestamp": timezone.now(),
                        "recorded_by": recorded_by,
                    }
                )
                if not created:
                    logger.info(f"Duplicate usage event ignored via idempotency key: {idempotency_key}")
                return record, created
        except IntegrityError:
            # Race condition catch: existing key was committed concurrently
            record = UsageRecord.objects.get(idempotency_key=idempotency_key)
            return record, False

    @staticmethod
    def get_tenant_usage_summary(tenant_id):
        """
        Calculates all usage metrics for the active billing cycle alongside quota limits.
        """
        subscription = EntitlementService.get_or_create_default_subscription(tenant_id)
        entitlements = PlanEntitlement.objects.filter(plan=subscription.plan)

        summary = []
        for ent in entitlements:
            metric_data = {
                "feature_key": ent.feature_key,
                "feature_type": ent.feature_type,
                "quota_limit": ent.quota_limit,
                "current_usage": 0,
                "remaining": None,
                "is_exceeded": False,
            }

            if ent.feature_type == "quota":
                usage_sum = UsageRecord.objects.filter(
                    tenant_id=tenant_id,
                    metric_name=ent.feature_key,
                    timestamp__gte=subscription.current_period_start - timezone.timedelta(minutes=5),
                    timestamp__lte=subscription.current_period_end,
                ).aggregate(total=Sum("quantity"))["total"] or 0

                metric_data["current_usage"] = usage_sum
                if ent.quota_limit is not None:
                    metric_data["remaining"] = max(0, ent.quota_limit - usage_sum)
                    metric_data["is_exceeded"] = usage_sum > ent.quota_limit

            summary.append(metric_data)

        return {
            "tenant_id": str(tenant_id),
            "plan_code": subscription.plan.code,
            "plan_name": subscription.plan.name,
            "subscription_status": subscription.status,
            "period_start": subscription.current_period_start.isoformat(),
            "period_end": subscription.current_period_end.isoformat(),
            "metrics": summary,
        }