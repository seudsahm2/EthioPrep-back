from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    class ExamType(models.TextChoices):
        GRADE12 = "grade12", "Grade 12 Entrance Exam"
        EXIT = "exit", "University Exit Exam"

    class Grade12Stream(models.TextChoices):
        NATURAL = "natural", "Natural"
        SOCIAL = "social", "Social"

    class PackageType(models.TextChoices):
        FREE = "free", "Free"
        SIMPLE = "simple", "Simple"
        DETAILED = "detailed", "Detailed"
        DEEP = "deep", "Deep"

    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    exam_type = models.CharField(max_length=20, choices=ExamType.choices, default=ExamType.GRADE12)
    grade12_stream = models.CharField(
        max_length=20,
        choices=Grade12Stream.choices,
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        "questions.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    package_type = models.CharField(max_length=20, choices=PackageType.choices, default=PackageType.FREE)
    created_at = models.DateTimeField(auto_now_add=True)
    google_sub = models.CharField(max_length=128, blank=True, null=True, unique=True)
    email_verified = models.BooleanField(default=False)

    simple_explanations_used = models.PositiveIntegerField(default=0)
    detailed_explanations_used = models.PositiveIntegerField(default=0)
    deep_explanations_used = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def set_package(self, package_type: str) -> None:
        self.package_type = package_type
        self.save(update_fields=["package_type"])

    def can_access_level(self, level: str) -> bool:
        if self.package_type == self.PackageType.DEEP:
            return True
        if self.package_type == self.PackageType.DETAILED and level in {"simple", "detailed"}:
            return True
        if self.package_type == self.PackageType.SIMPLE and level == "simple":
            return True

        limits = {"simple": 20, "detailed": 10, "deep": 5}
        used = {
            "simple": self.simple_explanations_used,
            "detailed": self.detailed_explanations_used,
            "deep": self.deep_explanations_used,
        }
        return used[level] < limits[level]

    def increment_explanation_usage(self, level: str) -> None:
        field_map = {
            "simple": "simple_explanations_used",
            "detailed": "detailed_explanations_used",
            "deep": "deep_explanations_used",
        }
        field = field_map[level]
        setattr(self, field, getattr(self, field) + 1)
        self.save(update_fields=[field])

    def __str__(self) -> str:
        # USERNAME_FIELD is email, but email is nullable for some accounts.
        # Admin list rendering requires __str__ to always return text.
        if self.email:
            return self.email
        if self.username:
            return self.username
        return f"user-{self.pk or 'unknown'}"


class StudyHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="study_history")
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=120, blank=True)
    correct = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


