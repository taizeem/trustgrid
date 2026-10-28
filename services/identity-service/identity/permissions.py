from rest_framework.permissions import BasePermission
from identity.models import Membership, RoleChoices

class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        target_org_id = view.kwargs.get("org_id") or getattr(request, "tenant_id", None)
        if not target_org_id:
            return False

        # If token is tenant-scoped, it must match the target organization
        token_tid = getattr(request, "tenant_id", None)
        if token_tid and str(token_tid) != str(target_org_id):
            return False

        return Membership.objects.filter(
            user=request.user,
            organization_id=target_org_id
        ).exists()


class IsTenantAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        target_org_id = view.kwargs.get("org_id") or getattr(request, "tenant_id", None)
        if not target_org_id:
            return False

        # If token is tenant-scoped, it must match the target organization
        token_tid = getattr(request, "tenant_id", None)
        if token_tid and str(token_tid) != str(target_org_id):
            return False

        return Membership.objects.filter(
            user=request.user,
            organization_id=target_org_id,
            role=RoleChoices.ADMIN
        ).exists()
