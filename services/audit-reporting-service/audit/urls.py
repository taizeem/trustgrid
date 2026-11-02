from django.urls import path

from audit.views import (
    AuditEventsListView,
    ComplianceReadinessReportView,
    ExportAuditLogsView,
    HealthCheckView,
    IngestAuditEventView,
    VendorRiskSummaryReportView,
)

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # Audit trail APIs
    path("api/v1/audit/events/", AuditEventsListView.as_view(), name="audit-events-list"),
    path("api/v1/audit/events/ingest/", IngestAuditEventView.as_view(), name="audit-events-ingest"),
    # Reporting APIs
    path("api/v1/reports/compliance-readiness/", ComplianceReadinessReportView.as_view(), name="report-compliance-readiness"),
    path("api/v1/reports/vendor-risk-summary/", VendorRiskSummaryReportView.as_view(), name="report-vendor-risk-summary"),
    path("api/v1/reports/audit-export/", ExportAuditLogsView.as_view(), name="report-audit-export"),
]