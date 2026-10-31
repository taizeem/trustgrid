from rest_framework.permissions import BasePermission

class IsTenantAuthenticated(BasePermission):
    """Requires the caller to be authenticated AND present a valid tenant context claim ('tid')."""
    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False
        return bool(getattr(request, "tenant_id", None))


def HasRole(allowed_roles):
    """
    Factory returning a BasePermission class requiring specific tenant roles like 'admin'.
    Compatible with Django REST Framework's permission_classes = [IsTenantAuthenticated, HasRole(['admin'])].
    """
    class RolePermission(BasePermission):
        def has_permission(self, request, view):
            if not request.user or not getattr(request.user, "is_authenticated", False):
                return False
            user_roles = getattr(request.user, "roles", [])
            return any(role in user_roles for role in allowed_roles)

    return RolePermission