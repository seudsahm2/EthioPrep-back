from django.contrib import admin

from .models import AIQuestionJob


@admin.register(AIQuestionJob)
class AIQuestionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "count", "difficulty", "status", "created_at")
    list_filter = ("status", "difficulty", "created_at")
    search_fields = ("user__email", "subject__name", "topic")
