from rest_framework.permissions import BasePermission

class IsTenantAuthenticated(BasePermission):
    """Requires the caller to be authenticated AND present a valid tenant context claim ('tid')."""
    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False
        return bool(getattr(request, "tenant_id", None))


class HasRole(BasePermission):
    """Factory permission requiring specific tenant roles like 'admin' or 'billing_manager'."""
    allowed_roles = []

    def __init__(self, allowed_roles=None):
        if allowed_roles:
            self.allowed_roles = allowed_roles

    def __call__(self):
        """Allows both HasRole(['admin']) instances and HasRole classes in permission_classes."""
        return self

    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False
        user_roles = getattr(request.user, "roles", [])
        return any(role in user_roles for role in self.allowed_roles)