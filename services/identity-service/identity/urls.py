from django.urls import path
from identity.views import (
    RegisterView,
    LoginView,
    TenantTokenExchangeView,
    OrganizationListCreateView,
    OrganizationDetailView,
    OrganizationMembersView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", LoginView.as_view(), name="token_obtain"),
    path("auth/token/tenant/", TenantTokenExchangeView.as_view(), name="token_tenant_exchange"),
    path("organizations/", OrganizationListCreateView.as_view(), name="org_list_create"),
    path("organizations/<uuid:org_id>/", OrganizationDetailView.as_view(), name="org_detail"),
    path("organizations/<uuid:org_id>/members/", OrganizationMembersView.as_view(), name="org_members"),
]
