import pytest
from django.db import IntegrityError
from identity.models import User, Organization, Membership, RoleChoices

@pytest.mark.django_db
def test_create_user_successful():
    user = User.objects.create_user(email="analyst@trustgrid.test", password="SecurePassword123!")
    assert user.email == "analyst@trustgrid.test"
    assert user.check_password("SecurePassword123!")
    assert not user.is_staff

@pytest.mark.django_db
def test_user_email_unique_constraint():
    User.objects.create_user(email="dup@trustgrid.test", password="password")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="dup@trustgrid.test", password="password2")

@pytest.mark.django_db
def test_membership_uniqueness():
    user = User.objects.create_user(email="member@trustgrid.test", password="password")
    org = Organization.objects.create(name="Test Org", slug="test-org")
    
    Membership.objects.create(user=user, organization=org, role=RoleChoices.ANALYST)
    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, organization=org, role=RoleChoices.ADMIN)
