import time
import jwt
from django.conf import settings

ROLE_PERMISSIONS = {
    "admin": [
        "tenant:read", "tenant:write", "tenant:members:manage",
        "vendor:read", "vendor:write", "vendor:delete",
        "assessment:read", "assessment:write", "assessment:submit",
        "workflow:read", "workflow:approve", "workflow:reject",
    ],
    "analyst": [
        "tenant:read",
        "vendor:read", "vendor:write",
        "assessment:read", "assessment:write", "assessment:submit",
        "workflow:read",
    ],
    "auditor": [
        "tenant:read",
        "vendor:read",
        "assessment:read",
        "workflow:read",
    ],
    "viewer": [
        "tenant:read",
        "vendor:read",
        "assessment:read",
    ],
}

def generate_jwt(user, organization_id=None, role=None):
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iss": "https://auth.trustgrid.internal",
        "aud": ["trustgrid-services"],
        "iat": now,
        "exp": now + settings.JWT_EXPIRATION_SECONDS,
    }
    
    if organization_id and role:
        payload["tid"] = str(organization_id)
        payload["roles"] = [role]
        payload["perms"] = ROLE_PERMISSIONS.get(role, [])
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

def decode_jwt(token_str):
    try:
        payload = jwt.decode(
            token_str,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=["trustgrid-services"],
        )
        return payload
    except jwt.PyJWTError:
        return None
