import json
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from billing.models import Plan, Invoice
from billing.serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    UsageIngestSerializer,
    CheckoutSessionRequestSerializer,
    PlanChangeSerializer,
    InvoiceSerializer,
)
from billing.permissions import IsTenantAuthenticated, HasRole
from billing.services.entitlements import EntitlementService
from billing.services.usage import UsageMeteringService
from billing.services.payment_provider import StripeSandboxAdapter

logger = logging.getLogger(__name__)

class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = Plan.objects.filter(is_active=True).prefetch_related("entitlements")
        return Response(PlanSerializer(plans, many=True).data)


class SubscriptionDetailView(APIView):
    permission_classes = [IsTenantAuthenticated]

    def get(self, request):
        sub = EntitlementService.get_or_create_default_subscription(request.tenant_id)
        return Response(SubscriptionSerializer(sub).data)


class PlanChangeView(APIView):
    permission_classes = [IsTenantAuthenticated, HasRole(["admin"])]

    def post(self, request):
        serializer = PlanChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_code = serializer.validated_data["plan_code"]
        target_plan = Plan.objects.filter(code=plan_code, is_active=True).first()
        if not target_plan:
            return Response(
                {"error": f"Plan with code '{plan_code}' does not exist or is inactive."},
                status=status.HTTP_404_NOT_FOUND
            )

        sub = EntitlementService.get_or_create_default_subscription(request.tenant_id)
        sub.plan = target_plan
        sub.status = "active"
        sub.save(update_fields=["plan", "status", "updated_at"])

        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class SubscriptionCancelView(APIView):
    permission_classes = [IsTenantAuthenticated, HasRole(["admin"])]

    def post(self, request):
        sub = EntitlementService.get_or_create_default_subscription(request.tenant_id)
        sub.cancel_at_period_end = True
        sub.save(update_fields=["cancel_at_period_end", "updated_at"])
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class EntitlementCheckView(APIView):
    permission_classes = [IsTenantAuthenticated]

    def get(self, request):
        feature_key = request.query_params.get("feature")
        if not feature_key:
            return Response(
                {"error": "Query parameter 'feature' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(request.query_params.get("quantity", 1))
        except ValueError:
            quantity = 1

        result = EntitlementService.check_feature_access(
            tenant_id=request.tenant_id,
            feature_key=feature_key,
            requested_increment=quantity
        )
        http_status = status.HTTP_200_OK if result["allowed"] else status.HTTP_403_FORBIDDEN
        return Response(result, status=http_status)


class UsageIngestView(APIView):
    permission_classes = [IsTenantAuthenticated]

    def post(self, request):
        serializer = UsageIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record, created = UsageMeteringService.record_usage(
            tenant_id=request.tenant_id,
            metric_name=serializer.validated_data["metric_name"],
            quantity=serializer.validated_data["quantity"],
            idempotency_key=serializer.validated_data["idempotency_key"],
            recorded_by=getattr(request.user, "id", None),
        )

        return Response(
            {
                "id": str(record.id),
                "metric_name": record.metric_name,
                "quantity": record.quantity,
                "idempotency_key": record.idempotency_key,
                "timestamp": record.timestamp.isoformat(),
                "created": created,
                "status": "recorded" if created else "idempotent_duplicate",
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class UsageSummaryView(APIView):
    permission_classes = [IsTenantAuthenticated]

    def get(self, request):
        summary = UsageMeteringService.get_tenant_usage_summary(request.tenant_id)
        return Response(summary)


class CheckoutSessionView(APIView):
    permission_classes = [IsTenantAuthenticated, HasRole(["admin"])]

    def post(self, request):
        serializer = CheckoutSessionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        session_info = StripeSandboxAdapter.create_checkout_session(
            tenant_id=request.tenant_id,
            plan_code=data["plan_code"],
            success_url=data.get("success_url"),
            cancel_url=data.get("cancel_url"),
        )
        return Response(session_info, status=status.HTTP_201_CREATED)


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        sig_header = request.headers.get("Stripe-Signature") or request.headers.get("X-Signature")
        raw_payload = request.body

        if not StripeSandboxAdapter.verify_webhook_signature(raw_payload, sig_header):
            return Response({"error": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event_dict = json.loads(raw_payload.decode("utf-8"))
            event_id = event_dict.get("id")
            event_type = event_dict.get("type")

            if not event_id or not event_type:
                return Response({"error": "Missing event id or type."}, status=status.HTTP_400_BAD_REQUEST)

            outcome = StripeSandboxAdapter.process_incoming_webhook(
                event_id=event_id,
                event_type=event_type,
                payload=event_dict,
            )
            return Response(outcome, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvoiceListView(APIView):
    permission_classes = [IsTenantAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.filter(tenant_id=request.tenant_id).order_by("-created_at")
        return Response(InvoiceSerializer(invoices, many=True).data)