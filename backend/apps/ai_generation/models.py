from django.db import models


class AIQuestionJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="ai_jobs")
    subject = models.ForeignKey("questions.Subject", on_delete=models.CASCADE)
    topic = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(max_length=20, default="mixed")
    count = models.PositiveIntegerField(default=5)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
