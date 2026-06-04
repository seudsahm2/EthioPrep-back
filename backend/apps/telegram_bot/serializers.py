from rest_framework import serializers


class TelegramStartPracticeSerializer(serializers.Serializer):
    subject = serializers.CharField(required=False, allow_blank=True)


class TelegramSubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.ChoiceField(choices=("A", "B", "C", "D", "a", "b", "c", "d"))
    level = serializers.ChoiceField(choices=("simple", "detailed", "deep"), default="simple")
