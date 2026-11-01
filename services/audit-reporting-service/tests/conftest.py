import uuid
import time
import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

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
def auth_headers():
    def _create_headers(tenant_id, roles=None, user_id=None, email="test@enterprise.test"):
        roles = roles or ["admin"]
        uid = user_id or str(uuid.uuid4())
        now = int(time.time())
        payload = {
            "sub": str(uid),
            "email": email,
            "iss": "https://auth.trustgrid.internal",
            "aud": ["trustgrid-services"],
            "iat": now,
            "exp": now + 3600,
            "tid": str(tenant_id),
            "roles": roles,
            "perms": ["audit:read", "audit:write"],
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    return _create_headers