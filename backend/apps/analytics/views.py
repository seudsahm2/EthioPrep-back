from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.exams.models import ExamResult, PracticeSession
from apps.questions.models import Subject
from apps.users.models import StudyHistory, User

from .gamification import (
    ensure_default_badges,
    get_or_create_profile,
    leaderboard_rows,
    points_history_payload,
    user_badges_payload,
)


class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        public_actions = {"platform_overview", "leaderboard"}
        if getattr(self, "action", None) in public_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request):
        user = request.user
        sessions = PracticeSession.objects.filter(user=user)
        total_questions = sessions.aggregate(total=Coalesce(Sum("total_questions"), 0))["total"]
        total_score = sessions.aggregate(score=Coalesce(Sum("score"), 0))["score"]
        accuracy = round((total_score / total_questions) * 100, 2) if total_questions else 0
        profile = get_or_create_profile(user)

        payload = {
            "questions_practiced": total_questions,
            "accuracy": accuracy,
            "sessions": sessions.count(),
            "points": profile.points,
            "streak": profile.current_streak,
            "best_streak": profile.best_streak,
        }
        return Response(payload)

    @action(detail=False, methods=["get"])
    def subject_accuracy(self, request):
        queryset = (
            StudyHistory.objects.filter(user=request.user)
            .values("subject")
            .annotate(correct=Coalesce(Sum("correct"), 0), total=Coalesce(Sum("total"), 0))
            .order_by("subject")
        )
        data = []
        for row in queryset:
            total = row["total"]
            acc = round((row["correct"] / total) * 100, 2) if total else 0
            data.append({"subject": row["subject"], "accuracy": acc, "correct": row["correct"], "total": total})
        return Response(data)

    @action(detail=False, methods=["get"])
    def weak_topics(self, request):
        queryset = (
            StudyHistory.objects.filter(user=request.user)
            .exclude(topic="")
            .values("subject", "topic")
            .annotate(correct=Coalesce(Sum("correct"), 0), total=Coalesce(Sum("total"), 0))
        )
        weak = []
        for row in queryset:
            if not row["total"]:
                continue
            accuracy = (row["correct"] / row["total"]) * 100
            if accuracy < 60:
                weak.append(
                    {
                        "subject": row["subject"],
                        "topic": row["topic"],
                        "accuracy": round(accuracy, 2),
                    }
                )
        weak.sort(key=lambda item: item["accuracy"])
        return Response(weak)

    @action(detail=False, methods=["get"])
    def study_history(self, request):
        entries = StudyHistory.objects.filter(user=request.user)[:100]
        data = [
            {
                "subject": entry.subject,
                "topic": entry.topic,
                "correct": entry.correct,
                "total": entry.total,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]
        return Response(data)

    @action(detail=False, methods=["get"])
    def platform_overview(self, request):
        grade12_subjects = Subject.objects.filter(exam_type="grade12")
        exit_subjects = Subject.objects.filter(exam_type="exit")

        payload = {
            "stats": {
                "questions": Subject.objects.aggregate(total=Coalesce(Sum("questions_count"), 0))["total"],
                "students": User.objects.filter(role="student").count(),
                "subjects": Subject.objects.count(),
                "pass_rate": 95,
            },
            "features": [
                {"title": "10,000+ Questions", "description": "Past exams, model exams, and AI-generated practice questions"},
                {"title": "3-Level Explanations", "description": "Simple, Detailed, and Deep explanations for every question"},
                {"title": "Gamification", "description": "Earn badges, maintain streaks, and compete on leaderboards"},
                {"title": "Smart Analytics", "description": "Track your progress and identify weak areas to focus on"},
                {"title": "Exam Simulation", "description": "Timed practice exams that mirror real exam conditions"},
                {"title": "AI-Powered", "description": "New questions generated daily using advanced AI technology"},
            ],
            "pricing": [
                {"tier": "Simple", "price": 50, "features": ["Simple explanations", "Basic progress tracking", "Practice mode"], "popular": False},
                {"tier": "Detailed", "price": 100, "features": ["Simple + Detailed explanations", "Full analytics dashboard", "Exam simulation", "Bookmarks"], "popular": True},
                {"tier": "Deep", "price": 200, "features": ["All explanation levels", "AI question generation", "Priority support", "All features unlocked"], "popular": False},
            ],
            "tracks": {
                "grade12": [
                    {"id": s.id, "name": s.name, "questions": s.questions_count}
                    for s in grade12_subjects.order_by("name")
                ],
                "exit": [
                    {"id": s.id, "name": s.name, "questions": s.questions_count}
                    for s in exit_subjects.order_by("name")
                ],
            },
        }
        return Response(payload)

    @action(detail=False, methods=["get"])
    def leaderboard(self, request):
        return Response(leaderboard_rows(limit=100))

    @action(detail=False, methods=["get"])
    def badges(self, request):
        ensure_default_badges()
        return Response(user_badges_payload(request.user))

    @action(detail=False, methods=["get"])
    def points_history(self, request):
        return Response(points_history_payload(request.user, limit=50))
