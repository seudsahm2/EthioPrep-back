from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "user",
            "user_name",
            "package_type",
            "amount",
            "payment_screenshot",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("user", "status", "rejection_reason", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return attrs

        package_type = attrs.get("package_type")
        if not package_type:
            return attrs

        if getattr(user, "package_type", None) == package_type:
            raise serializers.ValidationError(
                {"package_type": "You are already on this package."}
            )

        if Payment.objects.filter(user=user, package_type=package_type, status=Payment.Status.PENDING).exists():
            raise serializers.ValidationError(
                {"package_type": "You already have a pending request for this package."}
            )

        return attrs


class PaymentReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("approve", "reject"))
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        action = attrs.get("action")
        reason = (attrs.get("reason") or "").strip()
        if action == "reject" and not reason:
            raise serializers.ValidationError({"reason": "Rejection reason is required when rejecting."})
        attrs["reason"] = reason
        return attrs
