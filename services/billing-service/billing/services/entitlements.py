import logging
from django.utils import timezone
from django.db.models import Sum
from billing.models import Plan, Subscription, PlanEntitlement, UsageRecord

logger = logging.getLogger(__name__)

class EntitlementService:
    @staticmethod
    def get_or_create_default_subscription(tenant_id):
        """Retrieves tenant subscription or provisions default 14-day Free Tier trial."""
        sub = Subscription.objects.filter(tenant_id=tenant_id).select_related("plan").first()
        if sub:
            return sub

        free_plan = Plan.objects.filter(code="free", is_active=True).first()
        if not free_plan:
            free_plan = Plan.objects.create(
                code="free",
                name="Free Tier",
                description="Default starter plan with baseline quotas",
                price_cents=0,
                billing_interval="month",
                trial_days=14,
            )
            PlanEntitlement.objects.create(plan=free_plan, feature_key="max_vendors", feature_type="quota", quota_limit=5)
            PlanEntitlement.objects.create(plan=free_plan, feature_key="assessments_per_month", feature_type="quota", quota_limit=10)
            PlanEntitlement.objects.create(plan=free_plan, feature_key="api_access", feature_type="boolean")

        now = timezone.now()
        end_time = now + timezone.timedelta(days=free_plan.trial_days or 14)
        sub = Subscription.objects.create(
            tenant_id=tenant_id,
            plan=free_plan,
            status="trialing",
            current_period_start=now,
            current_period_end=end_time,
        )
        logger.info(f"Initialized default subscription for tenant {tenant_id} on plan {free_plan.code}")
        return sub

    @classmethod
    def check_feature_access(cls, tenant_id, feature_key, requested_increment=1):
        subscription = cls.get_or_create_default_subscription(tenant_id)

        if not subscription.is_currently_valid():
            return {
                "allowed": False,
                "reason": f"Subscription status is '{subscription.status}'. Active subscription required.",
                "feature_key": feature_key,
                "plan_code": subscription.plan.code,
            }

        entitlement = PlanEntitlement.objects.filter(
            plan=subscription.plan,
            feature_key=feature_key
        ).first()

        if not entitlement:
            return {
                "allowed": False,
                "reason": f"Feature '{feature_key}' is not included in plan '{subscription.plan.name}'.",
                "feature_key": feature_key,
                "plan_code": subscription.plan.code,
            }

        if entitlement.feature_type == "boolean":
            return {
                "allowed": True,
                "feature_key": feature_key,
                "feature_type": "boolean",
                "plan_code": subscription.plan.code,
            }

        quota_limit = entitlement.quota_limit
        if quota_limit is None:
            return {
                "allowed": True,
                "feature_key": feature_key,
                "feature_type": "quota",
                "quota_limit": None,
                "current_usage": 0,
                "remaining": None,
                "plan_code": subscription.plan.code,
            }

        usage_total = UsageRecord.objects.filter(
            tenant_id=tenant_id,
            metric_name=feature_key,
            timestamp__gte=subscription.current_period_start,
            timestamp__lte=subscription.current_period_end,
        ).aggregate(total=Sum("quantity"))["total"] or 0

        projected = usage_total + requested_increment
        allowed = projected <= quota_limit
        remaining = max(0, quota_limit - usage_total)

        return {
            "allowed": allowed,
            "feature_key": feature_key,
            "feature_type": "quota",
            "quota_limit": quota_limit,
            "current_usage": usage_total,
            "remaining": remaining,
            "plan_code": subscription.plan.code,
            "reason": None if allowed else f"Quota exceeded for '{feature_key}'. Limit: {quota_limit}, Used: {usage_total}."
        }