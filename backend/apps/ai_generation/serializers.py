from rest_framework import serializers

from .models import AIQuestionJob


class AIQuestionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQuestionJob
        fields = ("id", "subject", "topic", "difficulty", "count", "status", "error_message", "created_at")
        read_only_fields = ("status", "error_message", "created_at")
