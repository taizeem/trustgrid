from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from audit.models import AuditEvent, AuditSeverity

class ReportingService:
    @staticmethod
    def generate_compliance_readiness(organization_id):
        """
        Computes compliance readiness indicators based on logged tenant activities.
        """
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        events_qs = AuditEvent.objects.filter(organization_id=organization_id)
        recent_events = events_qs.filter(created_at__gte=thirty_days_ago)

        total_audit_events = events_qs.count()
        recent_event_count = recent_events.count()

        severity_counts = events_qs.values("severity").annotate(count=Count("id"))
        severity_map = {item["severity"]: item["count"] for item in severity_counts}

        # Calculate action breakdowns
        action_counts = events_qs.values("action").annotate(count=Count("id")).order_by("-count")[:10]

        # Calculate high-risk activity count
        critical_alerts = severity_map.get(AuditSeverity.CRITICAL, 0)
        warning_alerts = severity_map.get(AuditSeverity.WARNING, 0)

        # Baseline readiness score calculation (100 - weighted critical/warning deductions)
        score = 100
        if critical_alerts > 0:
            score -= min(40, critical_alerts * 10)
        if warning_alerts > 0:
            score -= min(20, warning_alerts * 2)

        readiness_score = max(0, score)

        return {
            "organization_id": str(organization_id),
            "generated_at": now.isoformat(),
            "period_days": 30,
            "readiness_score": readiness_score,
            "total_audit_events": total_audit_events,
            "recent_events_count": recent_event_count,
            "critical_events": critical_alerts,
            "warning_events": warning_alerts,
            "top_actions": list(action_counts),
        }

    @staticmethod
    def generate_vendor_risk_summary(organization_id):
        """
        Synthesizes vendor lifecycle and risk calculation audit events into an executive summary.
        """
        vendor_events = AuditEvent.objects.filter(
            organization_id=organization_id,
            resource_type__in=["vendor", "assessment", "risk_calculation"]
        )

        total_vendor_actions = vendor_events.count()
        action_breakdown = vendor_events.values("action").annotate(count=Count("id"))

        return {
            "organization_id": str(organization_id),
            "total_vendor_lifecycle_events": total_vendor_actions,
            "actions": {item["action"]: item["count"] for item in action_breakdown},
        }