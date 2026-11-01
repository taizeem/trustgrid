import csv
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from audit.models import AuditEvent
from audit.serializers import AuditEventSerializer, IngestAuditEventSerializer
from audit.permissions import IsTenantAuthenticated, CanViewAuditLogs
from audit.services.reporting_service import ReportingService

class StandardResultsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "healthy", "service": "audit-reporting-service"}, status=status.HTTP_200_OK)


class AuditEventsListView(APIView):
    """
    Searchable, filtered audit log history with strict tenant isolation.
    """
    permission_classes = [IsTenantAuthenticated, CanViewAuditLogs]
    pagination_class = StandardResultsPagination

    def get(self, request):
        tenant_id = request.tenant_id
        queryset = AuditEvent.objects.filter(organization_id=tenant_id)

        # Filters
        action = request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        resource_type = request.query_params.get("resource_type")
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        resource_id = request.query_params.get("resource_id")
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)

        severity = request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)

        actor_id = request.query_params.get("actor_id")
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)

        from_date = request.query_params.get("from_date")
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)

        to_date = request.query_params.get("to_date")
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(actor_email__icontains=search) |
                Q(action__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class IngestAuditEventView(APIView):
    """
    Direct synchronous endpoint for recording auditable events from other services or gateway.
    """
    permission_classes = [IsTenantAuthenticated]

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def post(self, request):
        serializer = IngestAuditEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event = AuditEvent.objects.create(
            organization_id=request.tenant_id,
            actor_id=data.get("actor_id") or str(request.user.id),
            actor_email=data.get("actor_email") or getattr(request.user, "email", ""),
            action=data["action"],
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            severity=data["severity"],
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            correlation_id=data.get("correlation_id", ""),
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:256],
        )

        return Response(AuditEventSerializer(event).data, status=status.HTTP_201_CREATED)


class ComplianceReadinessReportView(APIView):
    permission_classes = [IsTenantAuthenticated, CanViewAuditLogs]

    def get(self, request):
        report = ReportingService.generate_compliance_readiness(request.tenant_id)
        return Response(report, status=status.HTTP_200_OK)


class VendorRiskSummaryReportView(APIView):
    permission_classes = [IsTenantAuthenticated, CanViewAuditLogs]

    def get(self, request):
        report = ReportingService.generate_vendor_risk_summary(request.tenant_id)
        return Response(report, status=status.HTTP_200_OK)


class ExportAuditLogsView(APIView):
    """
    Exports tenant audit events as CSV or JSON format for compliance and audit evidence.
    """
    permission_classes = [IsTenantAuthenticated, CanViewAuditLogs]
    def perform_content_negotiation(self, request, force=False):
        # Bypass DRF's built-in format-suffix negotiation so ?format=csv or ?format=json
        # is handled directly by this view instead of raising 404 NotFound
        renderers = self.get_renderers()
        return (renderers[0], renderers[0].media_type)

    def get(self, request):
        tenant_id = request.tenant_id
        export_format = request.query_params.get("format", "csv").lower()
        events = AuditEvent.objects.filter(organization_id=tenant_id).order_by("-created_at")[:5000]

        if export_format == "json":
            serializer = AuditEventSerializer(events, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="trustgrid_audit_export_{tenant_id}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Event ID", "Timestamp", "Actor ID", "Actor Email",
            "Action", "Resource Type", "Resource ID", "Severity",
            "IP Address", "Correlation ID", "Checksum"
        ])

        for event in events:
            writer.writerow([
                str(event.id),
                event.created_at.isoformat(),
                event.actor_id,
                event.actor_email,
                event.action,
                event.resource_type,
                event.resource_id,
                event.severity,
                event.ip_address or "",
                event.correlation_id or "",
                event.checksum or "",
            ])

        return response