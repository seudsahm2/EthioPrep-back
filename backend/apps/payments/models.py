from django.db import models


class Payment(models.Model):
    class PackageType(models.TextChoices):
        SIMPLE = "simple", "Simple"
        DETAILED = "detailed", "Detailed"
        DEEP = "deep", "Deep"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="payments")
    package_type = models.CharField(max_length=20, choices=PackageType.choices)
    amount = models.PositiveIntegerField()
    payment_screenshot = models.ImageField(upload_to="payments/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True, default="")
    verified_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="verified_payments",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
