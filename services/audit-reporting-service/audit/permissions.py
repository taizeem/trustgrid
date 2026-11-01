from rest_framework.permissions import BasePermission

class IsTenantAuthenticated(BasePermission):
    """Requires caller to be authenticated and present a valid tenant organization claim ('tid')."""
    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False
        return bool(getattr(request, "tenant_id", None))


class CanViewAuditLogs(BasePermission):
    """
    Only tenant admins, analysts, or compliance auditors may view audit logs and reports.
    Viewers or external contractors are denied access.
    """
    ALLOWED_ROLES = {"admin", "auditor", "analyst"}

    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False
        user_roles = set(getattr(request.user, "roles", []))
        return bool(user_roles & self.ALLOWED_ROLES)