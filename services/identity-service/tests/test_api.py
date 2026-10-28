import pytest
from rest_framework import status
from identity.models import User, Organization

@pytest.mark.django_db
def test_user_registration_and_login_flow(api_client):
    reg_payload = {
        "email": "cto@enterprise.com",
        "first_name": "Chief",
        "last_name": "Architect",
        "password": "SecurePassword987!"
    }
    reg_resp = api_client.post("/api/v1/auth/register/", reg_payload, format="json")
    assert reg_resp.status_code == status.HTTP_201_CREATED
    assert "token" in reg_resp.data

    login_resp = api_client.post("/api/v1/auth/token/", {
        "email": "cto@enterprise.com",
        "password": "SecurePassword987!"
    }, format="json")
    assert login_resp.status_code == status.HTTP_200_OK
    assert "token" in login_resp.data

@pytest.mark.django_db
def test_create_organization_assigns_admin_role(api_client, create_user, auth_headers):
    user = create_user(email="owner@startup.io")
    headers = auth_headers(user)

    org_payload = {"name": "Startup Inc", "slug": "startup-inc"}
    resp = api_client.post("/api/v1/organizations/", org_payload, format="json", **headers)
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["role"] == "admin"
