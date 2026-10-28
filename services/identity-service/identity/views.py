import secrets
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from identity.models import Organization, Membership, Invitation, RoleChoices, InvitationStatus
from identity.tokens import generate_jwt
from identity.permissions import IsTenantMember, IsTenantAdmin
from identity.serializers import (
    UserRegistrationSerializer,
    LoginSerializer,
    TenantTokenExchangeSerializer,
    OrganizationSerializer,
    MembershipSerializer,
    CreateInvitationSerializer,
)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = generate_jwt(user)
        return Response({
            "user": serializer.data,
            "token": token
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        
        # Issue baseline user token
        token = generate_jwt(user)
        memberships = Membership.objects.filter(user=user).select_related("organization")
        orgs_data = [
            {"id": str(m.organization.id), "name": m.organization.name, "slug": m.organization.slug, "role": m.role}
            for m in memberships
        ]
        return Response({
            "token": token,
            "organizations": orgs_data
        })


class TenantTokenExchangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TenantTokenExchangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        membership = serializer.context["membership"]
        
        tenant_token = generate_jwt(
            user=request.user,
            organization_id=membership.organization.id,
            role=membership.role
        )
        return Response({"token": tenant_token})


class OrganizationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organizations = Organization.objects.filter(memberships__user=request.user)
        serializer = OrganizationSerializer(organizations, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        # The user creating the organization automatically becomes its Admin
        Membership.objects.create(
            user=request.user,
            organization=org,
            role=RoleChoices.ADMIN
        )
        return Response(OrganizationSerializer(org, context={"request": request}).data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request, org_id):
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrganizationSerializer(org, context={"request": request})
        return Response(serializer.data)


class OrganizationMembersView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated(), IsTenantMember()]

    def get(self, request, org_id):
        members = Membership.objects.filter(organization_id=org_id).select_related("user")
        serializer = MembershipSerializer(members, many=True)
        return Response(serializer.data)

    def post(self, request, org_id):
        serializer = CreateInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        
        invitation = Invitation.objects.create(
            organization_id=org_id,
            email=serializer.validated_data["email"],
            role=serializer.validated_data.get("role", RoleChoices.ANALYST),
            token=token,
            invited_by=request.user,
            expires_at=expires_at,
        )
        return Response({
            "invitation_id": str(invitation.id),
            "email": invitation.email,
            "token": invitation.token,
            "expires_at": invitation.expires_at
        }, status=status.HTTP_201_CREATED)
