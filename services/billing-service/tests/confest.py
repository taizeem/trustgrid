import uuid
import time
import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from billing.models import Plan, PlanEntitlement

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def tenant_a():
    return uuid.uuid4()

@pytest.fixture
def tenant_b():
    return uuid.uuid4()

@pytest.fixture
def create_jwt():
    def _make(user_id=None, tenant_id=None, roles=None, include_tid=True):
        uid = str(user_id or uuid.uuid4())
        payload = {
            "sub": uid,
            "email": "billing-admin@trustgrid.test",
            "roles": roles or ["admin"],
            "perms": ["billing:read", "billing:write"],
            "iss": "https://auth.trustgrid.internal",
            "aud": ["trustgrid-services"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        if include_tid:
            payload["tid"] = str(tenant_id) if tenant_id else str(uuid.uuid4())
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return _make

@pytest.fixture
def auth_headers(create_jwt):
    def _headers(user_id=None, tenant_id=None, roles=None, include_tid=True):
        token = create_jwt(user_id=user_id, tenant_id=tenant_id, roles=roles, include_tid=include_tid)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    return _headers

@pytest.fixture
def seed_plans(db):
    """Provisions standard tiered plans with entitlements."""
    free_plan = Plan.objects.create(
        code="free",
        name="Free Tier",
        description="Free tier for small vendors",
        price_cents=0,
        billing_interval="month",
        trial_days=14,
    )
    PlanEntitlement.objects.create(plan=free_plan, feature_key="max_vendors", feature_type="quota", quota_limit=5)
    PlanEntitlement.objects.create(plan=free_plan, feature_key="assessments_per_month", feature_type="quota", quota_limit=10)
    PlanEntitlement.objects.create(plan=free_plan, feature_key="api_access", feature_type="boolean")

    growth_plan = Plan.objects.create(
        code="growth",
        name="Growth Plan",
        description="Professional vendor compliance",
        price_cents=49900,
        billing_interval="month",
        trial_days=14,
    )
    PlanEntitlement.objects.create(plan=growth_plan, feature_key="max_vendors", feature_type="quota", quota_limit=50)
    PlanEntitlement.objects.create(plan=growth_plan, feature_key="assessments_per_month", feature_type="quota", quota_limit=100)
    PlanEntitlement.objects.create(plan=growth_plan, feature_key="api_access", feature_type="boolean")
    PlanEntitlement.objects.create(plan=growth_plan, feature_key="custom_risk_rules", feature_type="boolean")

    enterprise_plan = Plan.objects.create(
        code="enterprise",
        name="Enterprise",
        description="Unlimited enterprise scale",
        price_cents=199900,
        billing_interval="month",
        trial_days=30,
    )
    PlanEntitlement.objects.create(plan=enterprise_plan, feature_key="max_vendors", feature_type="quota", quota_limit=None)
    PlanEntitlement.objects.create(plan=enterprise_plan, feature_key="assessments_per_month", feature_type="quota", quota_limit=None)
    PlanEntitlement.objects.create(plan=enterprise_plan, feature_key="api_access", feature_type="boolean")
    PlanEntitlement.objects.create(plan=enterprise_plan, feature_key="custom_risk_rules", feature_type="boolean")
    PlanEntitlement.objects.create(plan=enterprise_plan, feature_key="dedicated_support", feature_type="boolean")

    return {
        "free": free_plan,
        "growth": growth_plan,
        "enterprise": enterprise_plan,
    }