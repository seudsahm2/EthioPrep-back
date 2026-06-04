from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from services.payment_service import PaymentService
from utils.permissions import IsAdminUserRole, is_admin_principal

from .models import Payment
from .serializers import PaymentReviewSerializer, PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer

    def get_serializer_class(self):
        if self.action == "review":
            return PaymentReviewSerializer
        return PaymentSerializer

    def get_queryset(self):
        if is_admin_principal(self.request.user):
            return Payment.objects.select_related("user").all()
        return Payment.objects.select_related("user").filter(user=self.request.user)

    def get_permissions(self):
        if self.action in {"meta"}:
            return [permissions.AllowAny()]
        if self.action in {"review"}:
            return [IsAdminUserRole()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        payment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")
        if action == "approve":
            payment = PaymentService.approve(payment, request.user)
        else:
            payment = PaymentService.reject(payment, request.user, reason=reason)

        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def meta(self, request):
        payload = {
            "bank_details": [
                {"bank": "Commercial Bank of Ethiopia (CBE)", "account": "1000123456789", "name": "EthioExamPrep PLC"},
                {"bank": "Dashen Bank", "account": "0012345678", "name": "EthioExamPrep PLC"},
                {"bank": "Awash Bank", "account": "013456789012", "name": "EthioExamPrep PLC"},
            ],
            "packages": [
                {"id": "simple", "tier": "Simple", "price": 50, "description": "Simple explanations for all questions", "features": ["Simple explanations", "Basic practice mode", "Progress tracking"]},
                {"id": "detailed", "tier": "Detailed", "price": 100, "description": "Simple + Detailed explanations", "features": ["Simple + Detailed explanations", "Exam simulation", "Full analytics", "Bookmarks"]},
                {"id": "deep", "tier": "Deep", "price": 200, "description": "All explanation levels unlocked", "features": ["All explanation levels", "AI-generated questions", "Priority support", "All features"]},
            ],
        }

        if request.user and request.user.is_authenticated:
            approved_packages = list(
                Payment.objects.filter(user=request.user, status=Payment.Status.APPROVED)
                .order_by("created_at")
                .values_list("package_type", flat=True)
                .distinct()
            )
            pending_packages = list(
                Payment.objects.filter(user=request.user, status=Payment.Status.PENDING)
                .order_by("created_at")
                .values_list("package_type", flat=True)
                .distinct()
            )
            latest_approved = (
                Payment.objects.filter(user=request.user, status=Payment.Status.APPROVED)
                .order_by("-updated_at", "-id")
                .first()
            )
            latest_rejected = (
                Payment.objects.filter(user=request.user, status=Payment.Status.REJECTED)
                .order_by("-updated_at", "-id")
                .first()
            )

            payload["user_payment_summary"] = {
                "current_package": request.user.package_type,
                "approved_packages": approved_packages,
                "pending_packages": pending_packages,
                "latest_approved_payment_id": latest_approved.id if latest_approved else None,
                "latest_rejected_payment_id": latest_rejected.id if latest_rejected else None,
                "latest_rejected_reason": latest_rejected.rejection_reason if latest_rejected else "",
            }

        return Response(payload)
