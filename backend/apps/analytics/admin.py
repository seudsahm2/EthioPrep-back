from django.contrib import admin

from .models import BadgeDefinition, GamificationProfile, PointTransaction, UserBadge


@admin.register(GamificationProfile)
class GamificationProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "points",
        "current_streak",
        "best_streak",
        "practice_answered",
        "exam_attempts",
        "badges_count",
        "updated_at",
    )
    search_fields = ("user__email", "user__username")
    list_select_related = ("user",)


@admin.register(BadgeDefinition)
class BadgeDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "points_reward", "sort_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "slug")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "earned_at")
    list_select_related = ("user", "badge")
    search_fields = ("user__email", "user__username", "badge__name", "badge__slug")


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "points", "source_type", "source_id", "created_at")
    list_select_related = ("user",)
    search_fields = ("user__email", "user__username", "action")
    list_filter = ("source_type",)
