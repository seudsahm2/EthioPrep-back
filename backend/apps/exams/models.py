from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.questions.models import Subject


class PracticeSession(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="practice_sessions")
    subject = models.ForeignKey("questions.Subject", on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.CharField(max_length=120, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]


class UserAnswer(models.Model):
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("questions.Question", on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "question")


class ExamResult(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="exam_results")
    blueprint = models.ForeignKey("exams.ExamBlueprint", on_delete=models.SET_NULL, null=True, blank=True, related_name="results")
    subject = models.CharField(max_length=100, default="Mixed")
    score = models.PositiveIntegerField(default=0)
    weighted_score = models.FloatField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    duration = models.PositiveIntegerField(help_text="Duration in seconds", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ExamBlueprint(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    exam_type = models.CharField(max_length=20, choices=Subject.ExamType.choices)
    grade12_stream = models.CharField(
        max_length=20,
        choices=Subject.Grade12Stream.choices,
        null=True,
        blank=True,
    )
    grade_level = models.PositiveSmallIntegerField(
        choices=Subject.GradeLevel.choices,
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        "questions.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exam_blueprints",
    )
    question_count = models.PositiveIntegerField(default=10)
    duration_minutes = models.PositiveIntegerField(default=60)
    passing_score = models.PositiveSmallIntegerField(default=50)
    instructions = models.TextField(blank=True)
    timed_sections = models.BooleanField(default=False)
    negative_marking_enabled = models.BooleanField(default=False)
    negative_mark_per_wrong = models.FloatField(default=0.25)
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=False)
    section_locking = models.BooleanField(default=False)
    adaptive_difficulty = models.BooleanField(default=False)
    fail_fast_enabled = models.BooleanField(default=False)
    fail_fast_min_failed_sections = models.PositiveIntegerField(default=1)
    anti_cheat_enabled = models.BooleanField(default=True)
    max_blur_warnings = models.PositiveIntegerField(default=3)
    auto_submit_on_anti_cheat = models.BooleanField(default=True)
    max_retake_attempts = models.PositiveIntegerField(null=True, blank=True)
    retake_cooldown_minutes = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_exam_blueprints",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        if self.exam_type == Subject.ExamType.GRADE12:
            if self.department_id:
                raise ValidationError("Grade 12 blueprints cannot set a department.")
        if self.exam_type == Subject.ExamType.EXIT:
            if not self.department_id:
                raise ValidationError("Exit exam blueprints require a department.")
            if self.grade12_stream:
                raise ValidationError("Exit exam blueprints cannot set a grade stream.")
            if self.grade_level:
                raise ValidationError("Exit exam blueprints cannot set a grade level.")

        if self.negative_mark_per_wrong < 0:
            raise ValidationError("Negative mark per wrong answer cannot be negative.")
        if self.max_retake_attempts is not None and self.max_retake_attempts < 1:
            raise ValidationError("Max retake attempts must be at least 1.")
        if self.fail_fast_min_failed_sections < 1:
            raise ValidationError("Fail-fast minimum failed sections must be at least 1.")
        if self.max_blur_warnings < 1:
            raise ValidationError("Max blur warnings must be at least 1.")


class ExamBlueprintSection(models.Model):
    class DifficultyRule(models.TextChoices):
        ANY = "any", "Any"
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class SourceRule(models.TextChoices):
        ANY = "any", "Any"
        PAST = "past_exam", "Past Exam"
        MODEL = "model_exam", "Model Exam"
        CLASS = "class_exam", "Class Exam"
        AI = "ai_generated", "AI Generated"

    blueprint = models.ForeignKey(ExamBlueprint, on_delete=models.CASCADE, related_name="sections")
    subject = models.ForeignKey("questions.Subject", on_delete=models.CASCADE, related_name="blueprint_sections")
    topic = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(max_length=20, choices=DifficultyRule.choices, default=DifficultyRule.ANY)
    source = models.CharField(max_length=20, choices=SourceRule.choices, default=SourceRule.ANY)
    question_count = models.PositiveIntegerField(default=3)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    pass_threshold_percentage = models.PositiveSmallIntegerField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.blueprint.name}: {self.subject.name} ({self.question_count})"

    def clean(self):
        if self.subject.exam_type != self.blueprint.exam_type:
            raise ValidationError("Section subject exam type must match blueprint exam type.")

        if self.blueprint.exam_type == Subject.ExamType.EXIT:
            if self.blueprint.department_id and self.subject.department_id != self.blueprint.department_id:
                raise ValidationError("Section subject department must match blueprint department.")

        if self.blueprint.exam_type == Subject.ExamType.GRADE12:
            if self.blueprint.grade12_stream and self.subject.grade12_stream != self.blueprint.grade12_stream:
                raise ValidationError("Section subject stream must match blueprint stream.")
            if self.blueprint.grade_level and self.subject.grade_level != self.blueprint.grade_level:
                raise ValidationError("Section subject grade level must match blueprint grade level.")

        if self.blueprint.timed_sections and not self.duration_minutes:
            raise ValidationError("Timed section exams require duration_minutes for every section.")
        if self.pass_threshold_percentage is not None and not (1 <= self.pass_threshold_percentage <= 100):
            raise ValidationError("Section pass threshold must be between 1 and 100.")
