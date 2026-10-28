from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from identity.models import User
from identity.tokens import decode_jwt

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token_str = auth_header.split(" ")[1]
        payload = decode_jwt(token_str)
        if not payload:
            raise AuthenticationFailed("Invalid or expired authentication token.")

        user_id = payload.get("sub")
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found or inactive.")

        # Attach claims directly to the request object for downstream controllers
        request.tenant_id = payload.get("tid")
        request.user_roles = payload.get("roles", [])
        request.user_perms = payload.get("perms", [])

        return (user, payload)
