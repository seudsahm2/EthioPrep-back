import json

from django.contrib import admin
from django import forms
from django.db import models as django_models
from django.contrib.admin.widgets import AdminTextareaWidget
from django.http import JsonResponse
from django.urls import path as url_path

from .models import Bookmark, Department, Question, Subject, normalize_rich_blocks


RICH_EXPLANATION_HELP = (
    "This field is prefilled with a rich template by default. Keep only blocks you need, fill values, and leave others empty. "
    "Supported block patterns can grow over time. "
    "Examples: text/markdown/code/math/table/image/chart/steps/hint/warning/reference. "
    "Example value: "
    "[{\"type\":\"markdown\",\"text\":\"### Idea\\nUse substitution\"},"
    "{\"type\":\"code\",\"language\":\"python\",\"text\":\"print('hello')\"},"
    "{\"type\":\"table\",\"headers\":[\"x\",\"f(x)\"],\"rows\":[[1,2],[2,4]]}]"
)


class QuestionAdminForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "simple_explanation_rich",
            "detailed_explanation_rich",
            "deep_explanation_rich",
        ):
            self.fields[field_name].help_text = RICH_EXPLANATION_HELP


def _collect_changed_paths(before, after, base_path: str = "") -> list[str]:
    diffs: list[str] = []

    if type(before) is not type(after):
        diffs.append(base_path or "$")
        return diffs

    if isinstance(before, dict):
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            cursor = f"{base_path}.{key}" if base_path else str(key)
            if key not in before or key not in after:
                diffs.append(cursor)
                continue
            diffs.extend(_collect_changed_paths(before[key], after[key], cursor))
        return diffs

    if isinstance(before, list):
        max_len = max(len(before), len(after))
        for idx in range(max_len):
            cursor = f"{base_path}[{idx}]" if base_path else f"[{idx}]"
            if idx >= len(before) or idx >= len(after):
                diffs.append(cursor)
                continue
            diffs.extend(_collect_changed_paths(before[idx], after[idx], cursor))
        return diffs

    if before != after:
        diffs.append(base_path or "$")
    return diffs


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "exam_type", "grade_level", "department", "questions_count")
    list_filter = ("exam_type", "grade_level", "department")
    search_fields = ("name", "department__name")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm
    list_display = ("id", "subject", "topic", "difficulty", "source", "year")
    list_filter = ("subject", "difficulty", "source", "year")
    search_fields = ("question_text", "topic")
    fieldsets = (
        (
            "Question Core",
            {
                "fields": (
                    "subject",
                    "topic",
                    "question_type",
                    "question_text",
                    "option_a",
                    "option_b",
                    "option_c",
                    "option_d",
                    "correct_answer",
                    "difficulty",
                    "source",
                    "year",
                )
            },
        ),
        (
            "Simple Explanation",
            {"fields": ("simple_explanation", "simple_explanation_rich")},
        ),
        (
            "Detailed Explanation",
            {"fields": ("detailed_explanation", "detailed_explanation_rich")},
        ),
        (
            "Deep Explanation",
            {"fields": ("deep_explanation", "deep_explanation_rich")},
        ),
    )
    formfield_overrides = {
        django_models.JSONField: {
            "widget": AdminTextareaWidget(
                attrs={
                    "rows": 12,
                    "style": "font-family: Consolas, 'Courier New', monospace;",
                }
            )
        }
    }

    class Media:
        js = ("admin/questions/question_json_validate.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url_path(
                "validate-rich-json/",
                self.admin_site.admin_view(self.validate_rich_json_view),
                name="questions_question_validate_rich_json",
            )
        ]
        return custom_urls + urls

    def validate_rich_json_view(self, request):
        if request.method != "POST":
            return JsonResponse({"valid": False, "error": "Method not allowed."}, status=405)

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "valid": False,
                    "error": "Invalid request payload."
                },
                status=400,
            )

        level = str(payload.get("level") or "simple").lower().strip()
        if level not in {"simple", "detailed", "deep"}:
            return JsonResponse({"valid": False, "error": "Invalid explanation level."}, status=400)

        raw_text = str(payload.get("raw") or "").strip()
        if not raw_text:
            return JsonResponse({"valid": False, "error": "Field is empty."}, status=400)

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return JsonResponse(
                {
                    "valid": False,
                    "error": f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
                },
                status=400,
            )

        normalized = normalize_rich_blocks(parsed, level)
        changed_paths = _collect_changed_paths(parsed, normalized)

        return JsonResponse(
            {
                "valid": True,
                "normalized": normalized,
                "autofix_count": len(changed_paths),
                "autofix_paths": changed_paths[:120],
            }
        )


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "created_at")
    search_fields = ("user__email", "question__question_text")
