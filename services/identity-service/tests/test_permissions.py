import pytest
from rest_framework import status
from identity.models import RoleChoices, Membership

@pytest.mark.django_db
def test_cross_tenant_access_blocked(api_client, create_user, create_org, auth_headers):
    user_a = create_user(email="alice@org-a.com")
    org_a = create_org(name="Org A", slug="org-a")
    Membership.objects.create(user=user_a, organization=org_a, role=RoleChoices.ADMIN)

    user_b = create_user(email="bob@org-b.com")
    org_b = create_org(name="Org B", slug="org-b")
    Membership.objects.create(user=user_b, organization=org_b, role=RoleChoices.ADMIN)

    # Bob attempts to access Org A's details using his Org B token
    headers = auth_headers(user_b, organization_id=org_b.id, role=RoleChoices.ADMIN)
    response = api_client.get(f"/api/v1/organizations/{org_a.id}/", **headers)

    # Strict isolation: must receive HTTP 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_analyst_cannot_invite_members(api_client, create_user, create_org, auth_headers):
    analyst = create_user(email="analyst@org-a.com")
    org = create_org(name="Org A", slug="org-a")
    Membership.objects.create(user=analyst, organization=org, role=RoleChoices.ANALYST)

    headers = auth_headers(analyst, organization_id=org.id, role=RoleChoices.ANALYST)
    payload = {"email": "newuser@org-a.com", "role": "analyst"}
    response = api_client.post(f"/api/v1/organizations/{org.id}/members/", payload, format="json", **headers)

    # Only Admin can invite members
    assert response.status_code == status.HTTP_403_FORBIDDEN
