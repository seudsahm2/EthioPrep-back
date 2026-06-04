from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.questions.models import Question
from apps.questions.serializers import QuestionListSerializer
from .serializers import TelegramStartPracticeSerializer, TelegramSubmitAnswerSerializer


class TelegramStartPracticeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TelegramStartPracticeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = serializer.validated_data.get("subject")
        queryset = Question.objects.select_related("subject").all()
        if subject:
            queryset = queryset.filter(subject__name__iexact=subject)
        question = queryset.order_by("?").first()
        if not question:
            return Response({"detail": "No questions found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionListSerializer(question).data)


class TelegramSubmitAnswerView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TelegramSubmitAnswerSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question_id = serializer.validated_data["question_id"]
        selected_option = serializer.validated_data["selected_option"].upper()
        level = serializer.validated_data["level"]

        question = Question.objects.get(id=question_id)
        is_correct = selected_option == question.correct_answer.upper()

        field_map = {
            "simple": question.simple_explanation,
            "detailed": question.detailed_explanation,
            "deep": question.deep_explanation,
        }
        explanation = field_map.get(level, question.simple_explanation)

        return Response({"is_correct": is_correct, "correct_answer": question.correct_answer, "explanation": explanation})
