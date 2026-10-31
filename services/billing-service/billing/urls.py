from django.urls import path
from billing.views import (
    PlanListView,
    SubscriptionDetailView,
    PlanChangeView,
    SubscriptionCancelView,
    EntitlementCheckView,
    UsageIngestView,
    UsageSummaryView,
    CheckoutSessionView,
    StripeWebhookView,
    InvoiceListView,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="billing-plans"),
    path("subscription/", SubscriptionDetailView.as_view(), name="billing-subscription"),
    path("subscription/change-plan/", PlanChangeView.as_view(), name="billing-change-plan"),
    path("subscription/cancel/", SubscriptionCancelView.as_view(), name="billing-cancel"),
    path("entitlements/check/", EntitlementCheckView.as_view(), name="billing-entitlement-check"),
    path("usage/", UsageIngestView.as_view(), name="billing-usage-ingest"),
    path("usage/summary/", UsageSummaryView.as_view(), name="billing-usage-summary"),
    path("checkout-session/", CheckoutSessionView.as_view(), name="billing-checkout-session"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="billing-stripe-webhook"),
    path("invoices/", InvoiceListView.as_view(), name="billing-invoices"),
]