from django.contrib import admin

from .models import ExamBlueprint, ExamBlueprintSection, ExamResult, PracticeSession, UserAnswer


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "score", "total_questions", "started_at", "completed_at")
    list_filter = ("subject", "started_at")


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "selected_option", "is_correct", "answered_at")
    list_filter = ("is_correct", "answered_at")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "score", "correct_answers", "wrong_answers", "duration", "created_at")
    list_filter = ("subject", "created_at")


class ExamBlueprintSectionInline(admin.TabularInline):
    model = ExamBlueprintSection
    extra = 1
    fields = ("subject", "topic", "difficulty", "source", "question_count", "duration_minutes", "sort_order")


@admin.register(ExamBlueprint)
class ExamBlueprintAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "exam_type",
        "department",
        "grade12_stream",
        "grade_level",
        "question_count",
        "timed_sections",
        "negative_marking_enabled",
        "section_locking",
        "is_active",
    )
    list_filter = ("exam_type", "is_active", "department", "grade12_stream", "grade_level")
    search_fields = ("name", "description")
    inlines = [ExamBlueprintSectionInline]
