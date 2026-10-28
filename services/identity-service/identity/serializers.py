from rest_framework import serializers
from django.contrib.auth import authenticate
from identity.models import User, Organization, Membership, Invitation, RoleChoices

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs["email"], password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class TenantTokenExchangeSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()

    def validate_organization_id(self, value):
        user = self.context["request"].user
        membership = Membership.objects.filter(user=user, organization_id=value).first()
        if not membership:
            raise serializers.ValidationError("You do not have active membership in this organization.")
        self.context["membership"] = membership
        return value


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "created_at", "role")
        read_only_fields = ("id", "created_at", "role")

    def get_role(self, obj):
        user = self.context["request"].user
        membership = obj.memberships.filter(user=user).first()
        return membership.role if membership else None


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "user_id", "user_email", "role", "created_at")
        read_only_fields = ("id", "created_at")


class CreateInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ("id", "email", "role", "expires_at", "created_at")
        read_only_fields = ("id", "created_at")
