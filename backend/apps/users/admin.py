from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import StudyHistory, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("email", "username", "role", "exam_type", "package_type", "is_active")
    list_filter = ("role", "exam_type", "package_type", "is_active")
    ordering = ("-created_at",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "EthioPrep",
            {
                "fields": (
                    "role",
                    "exam_type",
                    "department",
                    "package_type",
                    "simple_explanations_used",
                    "detailed_explanations_used",
                    "deep_explanations_used",
                )
            },
        ),
    )


@admin.register(StudyHistory)
class StudyHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "topic", "correct", "total", "created_at")
    list_filter = ("subject", "created_at")
    search_fields = ("user__email", "subject", "topic")
