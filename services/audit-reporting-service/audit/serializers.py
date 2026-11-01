from rest_framework import serializers
from audit.models import AuditEvent, AuditSeverity

class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "organization_id",
            "actor_id",
            "actor_email",
            "action",
            "resource_type",
            "resource_id",
            "severity",
            "description",
            "metadata",
            "ip_address",
            "user_agent",
            "correlation_id",
            "checksum",
            "created_at",
        ]
        read_only_fields = ["id", "checksum", "created_at"]


class IngestAuditEventSerializer(serializers.Serializer):
    """Payload for direct synchronous audit ingestion."""
    action = serializers.CharField(max_length=120)
    resource_type = serializers.CharField(max_length=64)
    resource_id = serializers.CharField(max_length=128)
    severity = serializers.ChoiceField(choices=AuditSeverity.choices, default=AuditSeverity.INFO)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.DictField(required=False, default=dict)
    actor_id = serializers.CharField(required=False, allow_blank=True, default="")
    actor_email = serializers.EmailField(required=False, allow_blank=True, default="")
    correlation_id = serializers.CharField(required=False, allow_blank=True, default="")