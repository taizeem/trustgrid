from rest_framework import serializers
from vendors.models import (
    Vendor,
    AssessmentTemplate,
    AssessmentSubmission,
    Evidence,
    VendorTier,
    VendorLifecycleState,
)

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = (
            "id",
            "name",
            "website",
            "tier",
            "lifecycle_state",
            "primary_contact_name",
            "primary_contact_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant_id"] = request.tenant_id
        validated_data["created_by_id"] = request.user.id
        return super().create(validated_data)


class AssessmentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentTemplate
        fields = (
            "id",
            "title",
            "version",
            "description",
            "is_published",
            "schema",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant_id"] = request.tenant_id
        validated_data["created_by_id"] = request.user.id
        return super().create(validated_data)


class AssessmentSubmissionSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    template_title = serializers.CharField(source="template.title", read_only=True)

    class Meta:
        model = AssessmentSubmission
        fields = (
            "id",
            "vendor",
            "vendor_name",
            "template",
            "template_title",
            "status",
            "answers",
            "submitted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "submitted_at", "created_at", "updated_at")

    def validate_vendor(self, value):
        request = self.context["request"]
        if value.tenant_id != request.tenant_id:
            raise serializers.ValidationError("Referenced vendor does not belong to this tenant.")
        return value

    def validate_template(self, value):
        request = self.context["request"]
        if value.tenant_id != request.tenant_id:
            raise serializers.ValidationError("Referenced template does not belong to this tenant.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant_id"] = request.tenant_id
        return super().create(validated_data)


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = (
            "id",
            "vendor",
            "submission",
            "title",
            "file_key",
            "file_hash",
            "content_type",
            "file_size_bytes",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant_id"] = request.tenant_id
        validated_data["uploaded_by_id"] = request.user.id
        return super().create(validated_data)