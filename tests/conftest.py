import json
import os
import time
import urllib.error
import urllib.request
import uuid

import jwt
import pytest

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8088")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as platform integration test")
    config.addinivalue_line("markers", "contracts: mark test as event contract test")

class ApiClient:
    """Zero-dependency HTTP client using Python standard library."""
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, json_data=None, headers=None, timeout=10.0):
        url = f"{self.base_url}/{path.lstrip('/')}"
        req_headers = headers.copy() if headers else {}
        body = None

        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                raw = resp.read().decode("utf-8")
                try:
                    data = json.loads(raw)
                except Exception:
                    data = raw
                return ResponseWrapper(status_code, data)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                data = json.loads(raw)
            except Exception:
                data = raw
            return ResponseWrapper(exc.code, data)

    def get(self, path, headers=None):
        return self.request("GET", path, headers=headers)

    def post(self, path, json=None, headers=None):
        return self.request("POST", path, json_data=json, headers=headers)


class ResponseWrapper:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data if isinstance(self._data, (dict, list)) else {}


@pytest.fixture(scope="session")
def gateway_url():
    return GATEWAY_URL


@pytest.fixture(scope="session")
def http_client():
    return ApiClient(GATEWAY_URL)


@pytest.fixture(scope="session")
def api_client(http_client):
    return http_client


@pytest.fixture
def make_tenant_token():
    def _generator(tenant_id=None, user_id=None, email=None, roles=None, perms=None):
        t_id = str(tenant_id or uuid.uuid4())
        u_id = str(user_id or uuid.uuid4())
        user_email = email or f"user-{uuid.uuid4().hex[:6]}@enterprise.test"
        user_roles = roles or ["admin"]
        user_perms = perms or ["vendor:write", "assessment:write", "assessment:submit", "workflow:approve", "audit:read"]
        now = int(time.time())

        payload = {
            "sub": u_id,
            "email": user_email,
            "iss": "https://auth.trustgrid.internal",
            "aud": ["trustgrid-services"],
            "iat": now,
            "exp": now + 3600,
            "tid": t_id,
            "roles": user_roles,
            "perms": user_perms,
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, t_id, u_id
    return _generator