import uuid
from django.db import models

class VendorTier(models.TextChoices):
    TIER_1 = "tier_1", "Critical / High Risk"
    TIER_2 = "tier_2", "Significant / Medium Risk"
    TIER_3 = "tier_3", "Low Risk"


class VendorLifecycleState(models.TextChoices):
    PROSPECTIVE = "prospective", "Prospective"
    ACTIVE = "active", "Active"
    UNDER_REVIEW = "under_review", "Under Review"
    SUSPENDED = "suspended", "Suspended"
    OFFBOARDED = "offboarded", "Offboarded"


class Vendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=255, blank=True)
    tier = models.CharField(max_length=20, choices=VendorTier.choices, default=VendorTier.TIER_3)
    lifecycle_state = models.CharField(
        max_length=20, choices=VendorLifecycleState.choices, default=VendorLifecycleState.PROSPECTIVE
    )
    primary_contact_name = models.CharField(max_length=150, blank=True)
    primary_contact_email = models.EmailField(max_length=255, blank=True)
    created_by_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_profiles"
        indexes = [
            models.Index(fields=["tenant_id", "lifecycle_state"], name="idx_vendor_tenant_state"),
            models.Index(fields=["tenant_id", "name"], name="idx_vendor_tenant_name"),
        ]

    def __str__(self):
        return f"{self.name} [{self.lifecycle_state}]"


class AssessmentTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    # Structured questionnaire definition (sections, questions, weights)
    schema = models.JSONField(default=dict)
    created_by_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_templates"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "title", "version"],
                name="unique_template_version_per_tenant"
            )
        ]

    def __str__(self):
        return f"{self.title} (v{self.version})"


class AssessmentSubmissionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AssessmentSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="assessments")
    template = models.ForeignKey(AssessmentTemplate, on_delete=models.PROTECT, related_name="submissions")
    status = models.CharField(
        max_length=20,
        choices=AssessmentSubmissionStatus.choices,
        default=AssessmentSubmissionStatus.DRAFT
    )
    # Key-value response dictionary: {"q_encrypt_at_rest": true, "q_soc2_report": "attached"}
    answers = models.JSONField(default=dict)
    submitted_by_id = models.UUIDField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_submissions"
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_assessment_tenant_status"),
        ]

    def __str__(self):
        return f"Assessment for {self.vendor.name} [{self.status}]"


class Evidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="evidence_files")
    submission = models.ForeignKey(
        AssessmentSubmission, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence_files"
    )
    title = models.CharField(max_length=255)
    file_key = models.CharField(max_length=512, help_text="S3 object storage key")
    file_hash = models.CharField(max_length=64, help_text="SHA-256 digest")
    content_type = models.CharField(max_length=100)
    file_size_bytes = models.BigIntegerField()
    uploaded_by_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vendor_evidence"

    def __str__(self):
        return f"Evidence: {self.title} ({self.vendor.name})"