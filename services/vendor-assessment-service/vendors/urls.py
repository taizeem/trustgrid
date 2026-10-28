from django.urls import path
from vendors.views import (
    VendorListCreateView,
    VendorDetailView,
    TemplateListCreateView,
    TemplateDetailView,
    AssessmentSubmissionListCreateView,
    AssessmentSubmissionDetailView,
    AssessmentSubmitActionView,
)

urlpatterns = [
    path("vendors/", VendorListCreateView.as_view(), name="vendor_list_create"),
    path("vendors/<uuid:vendor_id>/", VendorDetailView.as_view(), name="vendor_detail"),
    path("templates/", TemplateListCreateView.as_view(), name="template_list_create"),
    path("templates/<uuid:template_id>/", TemplateDetailView.as_view(), name="template_detail"),
    path("assessments/", AssessmentSubmissionListCreateView.as_view(), name="assessment_list_create"),
    path("assessments/<uuid:submission_id>/", AssessmentSubmissionDetailView.as_view(), name="assessment_detail"),
    path("assessments/<uuid:submission_id>/submit/", AssessmentSubmitActionView.as_view(), name="assessment_submit"),
]