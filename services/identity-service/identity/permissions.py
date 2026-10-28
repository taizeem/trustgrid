from rest_framework.permissions import BasePermission
from identity.models import Membership, RoleChoices

class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant_id = getattr(request, "tenant_id", None) or view.kwargs.get("org_id")
        if not tenant_id:
            return False
        return Membership.objects.filter(
            user=request.user,
            organization_id=tenant_id
        ).exists()


class IsTenantAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant_id = getattr(request, "tenant_id", None) or view.kwargs.get("org_id")
        if not tenant_id:
            return False
        return Membership.objects.filter(
            user=request.user,
            organization_id=tenant_id,
            role=RoleChoices.ADMIN
        ).exists()
