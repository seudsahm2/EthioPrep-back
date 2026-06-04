from django.core.cache import cache
from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from utils.permissions import IsAdminUserRole

from .models import Bookmark, Department, Question, Subject
from .scoping import scope_question_queryset_for_user, scope_subject_queryset_for_user
from .serializers import (
    BookmarkSerializer,
    DepartmentSerializer,
    ExplanationSerializer,
    QuestionListSerializer,
    QuestionSerializer,
    SubjectSerializer,
)


class SubjectViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Subject.objects.select_related("department").all().order_by("name")
        queryset = scope_subject_queryset_for_user(queryset, self.request.user)
        exam_type = self.request.query_params.get("exam_type")
        grade_level = self.request.query_params.get("grade_level")
        department_id = self.request.query_params.get("department_id")
        grade12_stream = self.request.query_params.get("grade12_stream")

        if exam_type in {Subject.ExamType.GRADE12, Subject.ExamType.EXIT}:
            queryset = queryset.filter(exam_type=exam_type)
        if grade_level:
            queryset = queryset.filter(grade_level=grade_level)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if exam_type == Subject.ExamType.GRADE12 and grade12_stream in {"natural", "social"}:
            queryset = queryset.filter(Q(grade12_stream=grade12_stream) | Q(grade12_stream__isnull=True))

        return queryset

    def list(self, request, *args, **kwargs):
        if request.query_params or request.user.is_authenticated:
            return super().list(request, *args, **kwargs)

        cache_key = "subjects:list"
        payload = cache.get(cache_key)
        if payload is not None:
            return Response(payload)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def catalog(self, request):
        grade_subjects = Subject.objects.filter(exam_type=Subject.ExamType.GRADE12)
        requested_stream = request.query_params.get("grade12_stream")
        if requested_stream in {"natural", "social"}:
            grade_subjects = grade_subjects.filter(Q(grade12_stream=requested_stream) | Q(grade12_stream__isnull=True))
        grade_subjects = grade_subjects.order_by("grade_level", "name")
        departments = DepartmentSerializer(Department.objects.all(), many=True).data

        grouped = {"9": [], "10": [], "11": [], "12": []}
        for subject in grade_subjects:
            if subject.grade_level:
                grouped[str(subject.grade_level)].append(
                    {
                        "id": subject.id,
                        "name": subject.name,
                        "questions_count": subject.questions_count,
                    }
                )

        return Response(
            {
                "departments": departments,
                "grade_courses": grouped,
            }
        )


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related("subject").all()
    filterset_fields = ["subject", "difficulty", "source", "year", "subject__grade_level", "subject__department"]
    search_fields = ["question_text", "topic", "subject__name"]
    ordering_fields = ["created_at", "year"]

    def get_queryset(self):
        queryset = Question.objects.select_related("subject", "subject__department").all()
        return scope_question_queryset_for_user(queryset, self.request.user)

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminUserRole()]
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "explanation":
            return ExplanationSerializer
        if self.action == "list":
            return QuestionListSerializer
        return QuestionSerializer

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def explanation(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        level = serializer.validated_data["level"]

        if not request.user.can_access_level(level):
            return Response(
                {"detail": f"{level.title()} explanation limit reached. Please upgrade your package."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        question = self.get_object()
        request.user.increment_explanation_usage(level)
        payload = question.get_explanation_payload(level)
        return Response(payload)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, pk=None):
        question = self.get_object()
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, question=question)
        return Response({"created": created, "bookmark_id": bookmark.id})

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def bookmarks(self, request):
        queryset = Bookmark.objects.filter(user=request.user).select_related("question", "question__subject")
        page = self.paginate_queryset(queryset)
        serializer = BookmarkSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def random(self, request):
        subject = request.query_params.get("subject")
        qs = scope_question_queryset_for_user(
            Question.objects.select_related("subject", "subject__department").all(),
            request.user,
        )
        if subject:
            qs = qs.filter(subject__name__iexact=subject)
        question = qs.order_by("?").first()
        if question is None:
            return Response({"detail": "No questions available."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionListSerializer(question).data)
