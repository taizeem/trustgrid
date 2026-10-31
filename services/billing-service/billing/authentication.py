import uuid
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class TokenUser:
    """Represents an authenticated principal reconstructed purely from verified JWT claims."""
    def __init__(self, user_id, email, tenant_id, roles, perms):
        self.id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        self.email = email
        self.tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) and tenant_id else None
        self.roles = roles or []
        self.perms = perms or []
        self.is_authenticated = True

    def __str__(self):
        return f"TokenUser({self.email}, tenant={self.tenant_id})"


class StatelessJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token_str = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token_str,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                audience=["trustgrid-services"],
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed(f"Invalid token: {str(exc)}")

        user_id = payload.get("sub")
        tenant_id = payload.get("tid")
        email = payload.get("email", "")
        roles = payload.get("roles", [])
        perms = payload.get("perms", [])

        if not user_id:
            raise AuthenticationFailed("Token missing 'sub' claim.")

        user = TokenUser(user_id=user_id, email=email, tenant_id=tenant_id, roles=roles, perms=perms)
        request.tenant_id = user.tenant_id
        return (user, payload)