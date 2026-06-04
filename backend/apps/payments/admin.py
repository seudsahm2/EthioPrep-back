from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "package_type", "amount", "status", "created_at")
    list_filter = ("package_type", "status", "created_at")
    search_fields = ("user__email", "user__username")
