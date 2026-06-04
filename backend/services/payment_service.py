from apps.payments.models import Payment


class PaymentService:
    @staticmethod
    def approve(payment: Payment, admin_user) -> Payment:
        payment.status = Payment.Status.APPROVED
        payment.rejection_reason = ""
        payment.verified_by = admin_user
        payment.save(update_fields=["status", "rejection_reason", "verified_by", "updated_at"])
        payment.user.set_package(payment.package_type)
        return payment

    @staticmethod
    def reject(payment: Payment, admin_user, reason: str = "") -> Payment:
        payment.status = Payment.Status.REJECTED
        payment.rejection_reason = (reason or "").strip()
        payment.verified_by = admin_user
        payment.save(update_fields=["status", "rejection_reason", "verified_by", "updated_at"])
        return payment
