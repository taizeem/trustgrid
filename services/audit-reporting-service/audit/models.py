import uuid
import hashlib
import json
from django.db import models
from django.core.exceptions import PermissionDenied

class AuditSeverity(models.TextChoices):
    INFO = "INFO", "Information"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical"

class AuditEvent(models.Model):
    """
    Immutable audit log entry.
    Once created, modification or deletion is strictly forbidden to preserve
    tamper-evident compliance trail (SOC 2, ISO 27001).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    actor_id = models.CharField(max_length=128, db_index=True, blank=True, default="system")
    actor_email = models.EmailField(blank=True, default="")
    action = models.CharField(max_length=120, db_index=True)
    resource_type = models.CharField(max_length=64, db_index=True)
    resource_id = models.CharField(max_length=128, db_index=True)
    severity = models.CharField(
        max_length=16,
        choices=AuditSeverity.choices,
        default=AuditSeverity.INFO,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True, default="")
    correlation_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    checksum = models.CharField(max_length=64, editable=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization_id", "-created_at"], name="idx_audit_org_time"),
            models.Index(fields=["organization_id", "action", "-created_at"], name="idx_audit_org_act_time"),
            models.Index(fields=["organization_id", "resource_type", "resource_id"], name="idx_audit_org_resource"),
        ]

    def _compute_checksum(self):
        """Generates SHA-256 integrity hash across immutable fields."""
        data_str = f"{self.organization_id}|{self.actor_id}|{self.action}|{self.resource_type}|{self.resource_id}|{self.created_at or ''}|{json.dumps(self.metadata, sort_keys=True)}"
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.ip_address:
            self.ip_address = None
        if self.pk and not getattr(self._state, "adding", True):
            if AuditEvent.objects.filter(pk=self.pk).exists():
                raise PermissionDenied("Audit events are immutable and cannot be updated.")
        if not self.checksum:
            self.checksum = self._compute_checksum()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit events cannot be deleted.")

    def __str__(self):
        return f"[{self.severity}] {self.action} on {self.resource_type}:{self.resource_id} by {self.actor_email or self.actor_id}"


class IngestedMessageId(models.Model):
    """
    Tracks idempotency keys and CloudEvents message IDs consumed from RabbitMQ
    to guarantee exactly-once processing of duplicate message deliveries.
    """
    message_id = models.CharField(max_length=128, primary_key=True)
    event_type = models.CharField(max_length=120)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ingested_messages"

    def __str__(self):
        return f"Message({self.message_id}, type={self.event_type})"