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
def create_jwt():
    def _make(user_id=None, tenant_id=None, roles=None, include_tid=True):
        uid = str(user_id or uuid.uuid4())
        payload = {
            "sub": uid,
            "email": "analyst@trustgrid.test",
            "roles": roles or ["analyst"],
            "perms": ["vendor:read", "vendor:write"],
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