from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "status": "healthy",
        "service": "billing-service",
        "version": "0.1.0"
    })

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/v1/billing/", include("billing.urls")),
]