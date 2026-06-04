from django.db import models


class GamificationProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="gamification_profile")
    points = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    practice_answered = models.PositiveIntegerField(default=0)
    practice_correct = models.PositiveIntegerField(default=0)
    practice_sessions = models.PositiveIntegerField(default=0)

    exam_attempts = models.PositiveIntegerField(default=0)
    exam_answered = models.PositiveIntegerField(default=0)
    exam_correct = models.PositiveIntegerField(default=0)
    perfect_exams = models.PositiveIntegerField(default=0)

    total_answered = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)
    badges_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-points", "-best_streak", "user_id"]


class BadgeDefinition(models.Model):
    class Category(models.TextChoices):
        STREAK = "streak", "Streak"
        PRACTICE = "practice", "Practice"
        EXAM = "exam", "Exam"
        ACCURACY = "accuracy", "Accuracy"
        POINTS = "points", "Points"
        MILESTONE = "milestone", "Milestone"

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=240)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.MILESTONE)
    points_reward = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]


class UserBadge(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(BadgeDefinition, on_delete=models.CASCADE, related_name="earned_by")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")
        ordering = ["-earned_at"]


class PointTransaction(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="point_transactions")
    action = models.CharField(max_length=120)
    points = models.IntegerField()
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
