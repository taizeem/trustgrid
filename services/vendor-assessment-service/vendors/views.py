from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from vendors.models import Vendor, AssessmentTemplate, AssessmentSubmission, AssessmentSubmissionStatus
from vendors.serializers import (
    VendorSerializer,
    AssessmentTemplateSerializer,
    AssessmentSubmissionSerializer,
)

class TenantScopedQuerySetMixin:
    """Guarantees that every database operation is automatically filtered by the caller's tenant_id."""
    def get_queryset(self):
        return self.queryset.filter(tenant_id=self.request.tenant_id)


class VendorListCreateView(TenantScopedQuerySetMixin, ListCreateAPIView):
    queryset = Vendor.objects.all().order_by("-created_at")
    serializer_class = VendorSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tier = self.request.query_params.get("tier")
        state = self.request.query_params.get("lifecycle_state")
        search = self.request.query_params.get("search")
        if tier:
            qs = qs.filter(tier=tier)
        if state:
            qs = qs.filter(lifecycle_state=state)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class VendorDetailView(TenantScopedQuerySetMixin, RetrieveUpdateDestroyAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    lookup_url_kwarg = "vendor_id"


class TemplateListCreateView(TenantScopedQuerySetMixin, ListCreateAPIView):
    queryset = AssessmentTemplate.objects.all().order_by("-created_at")
    serializer_class = AssessmentTemplateSerializer


class TemplateDetailView(TenantScopedQuerySetMixin, RetrieveUpdateDestroyAPIView):
    queryset = AssessmentTemplate.objects.all()
    serializer_class = AssessmentTemplateSerializer
    lookup_url_kwarg = "template_id"


class AssessmentSubmissionListCreateView(TenantScopedQuerySetMixin, ListCreateAPIView):
    queryset = AssessmentSubmission.objects.all().order_by("-created_at")
    serializer_class = AssessmentSubmissionSerializer


class AssessmentSubmissionDetailView(TenantScopedQuerySetMixin, RetrieveUpdateDestroyAPIView):
    queryset = AssessmentSubmission.objects.all()
    serializer_class = AssessmentSubmissionSerializer
    lookup_url_kwarg = "submission_id"


class AssessmentSubmitActionView(APIView):
    """Transitions a draft assessment into 'submitted' status and timestamps the action."""
    def post(self, request, submission_id):
        try:
            submission = AssessmentSubmission.objects.get(id=submission_id, tenant_id=request.tenant_id)
        except AssessmentSubmission.DoesNotExist:
            return Response({"detail": "Assessment submission not found."}, status=status.HTTP_404_NOT_FOUND)

        if submission.status != AssessmentSubmissionStatus.DRAFT:
            return Response(
                {"detail": f"Cannot submit an assessment in '{submission.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission.status = AssessmentSubmissionStatus.SUBMITTED
        submission.submitted_by_id = request.user.id
        submission.submitted_at = timezone.now()
        submission.save(update_fields=["status", "submitted_by_id", "submitted_at", "updated_at"])

        serializer = AssessmentSubmissionSerializer(submission, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)