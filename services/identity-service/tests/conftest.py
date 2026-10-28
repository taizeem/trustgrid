import pytest
from rest_framework.test import APIClient
from identity.models import User, Organization, Membership, RoleChoices
from identity.tokens import generate_jwt

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user():
    def _create(email="user@trustgrid.test", password="TestPassword123!"):
        return User.objects.create_user(email=email, password=password)
    return _create

@pytest.fixture
def create_org():
    def _create(name="Acme Corp", slug="acme"):
        return Organization.objects.create(name=name, slug=slug)
    return _create

@pytest.fixture
def auth_headers():
    def _headers(user, organization_id=None, role=None):
        token = generate_jwt(user, organization_id=organization_id, role=role)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    return _headers
