from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
import random
from datetime import timedelta

from apps.questions.models import Question
from apps.questions.scoping import scope_question_queryset_for_user
from apps.users.models import User
from utils.permissions import IsAdminUserRole, is_admin_principal
from apps.analytics.gamification import record_exam_result_event, record_practice_answer_event, record_practice_session_start
from apps.analytics.realtime import emit_leaderboard_update

from .models import ExamBlueprint, ExamResult, PracticeSession
from .serializers import (
    ExamBlueprintSerializer,
    ExamResultSerializer,
    PracticeAnswerRequestSerializer,
    PracticeCompleteSerializer,
    PracticeSessionSerializer,
    UserAnswerSerializer,
)


class PracticeSessionViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PracticeSessionSerializer

    def get_queryset(self):
        return PracticeSession.objects.filter(user=self.request.user).select_related("subject")

    def get_serializer_class(self):
        if self.action == "answer":
            return PracticeAnswerRequestSerializer
        if self.action == "complete":
            return PracticeCompleteSerializer
        return PracticeSessionSerializer

    @action(detail=False, methods=["post"])
    def start(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = PracticeSession.objects.create(user=request.user, **serializer.validated_data)
        gamification = record_practice_session_start(request.user)
        emit_leaderboard_update()
        return Response({"session": PracticeSessionSerializer(session).data, "gamification": gamification}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def answer(self, request):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        session_id = input_serializer.validated_data["session_id"]
        session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
        answer_serializer = UserAnswerSerializer(
            data={
                "question": input_serializer.validated_data["question"].id,
                "selected_option": input_serializer.validated_data["selected_option"],
            },
            context={"request": request, "session": session},
        )
        answer_serializer.is_valid(raise_exception=True)
        answer = answer_serializer.save()
        gamification = record_practice_answer_event(
            user=request.user,
            is_correct=answer.is_correct,
            session_id=session.id,
            subject=session.subject.name if session.subject else "Mixed",
        )
        emit_leaderboard_update()
        return Response(
            {
                "is_correct": answer.is_correct,
                "score": session.score,
                "total_questions": session.total_questions,
                "gamification": gamification,
            }
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        session = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"session": session})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PracticeSessionSerializer(session).data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = PracticeSessionSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class ExamResultViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ExamResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExamResult.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blueprint = serializer.validated_data.get("blueprint")
        if blueprint and not self._can_user_access_blueprint(blueprint, request.user):
            raise PermissionDenied("Blueprint is outside your exam track.")

        exam_result = serializer.save(user=request.user)
        gamification = record_exam_result_event(request.user, exam_result)
        emit_leaderboard_update()

        output = self.get_serializer(exam_result)
        headers = self.get_success_headers(output.data)
        return Response({"result": output.data, "gamification": gamification}, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        # Kept for compatibility; create() handles save + gamification response contract.
        serializer.save(user=self.request.user)

    def _shuffle_question_options(self, payload_item: dict):
        options = list(payload_item.get("options", []))
        correct_index = payload_item.get("correct", 0)
        paired = list(enumerate(options))
        random.shuffle(paired)
        payload_item["options"] = [value for _, value in paired]
        for new_index, (old_index, _) in enumerate(paired):
            if old_index == correct_index:
                payload_item["correct"] = new_index
                break

    def _section_key(self, section) -> str:
        return f"section-{section.id}"

    def _enforce_retake_policy(self, blueprint: ExamBlueprint, user: User):
        attempts_qs = ExamResult.objects.filter(user=user, blueprint=blueprint).order_by("-created_at")
        attempts_count = attempts_qs.count()

        if blueprint.max_retake_attempts and attempts_count >= blueprint.max_retake_attempts:
            return (
                False,
                Response(
                    {
                        "detail": "Retake limit reached for this exam blueprint.",
                        "code": "retake_limit_reached",
                        "max_retake_attempts": blueprint.max_retake_attempts,
                        "attempts_used": attempts_count,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                ),
            )

        if blueprint.retake_cooldown_minutes > 0:
            latest_attempt = attempts_qs.first()
            if latest_attempt:
                cooldown_until = latest_attempt.created_at + timedelta(minutes=blueprint.retake_cooldown_minutes)
                if cooldown_until > timezone.now():
                    return (
                        False,
                        Response(
                            {
                                "detail": "Retake cooldown is active.",
                                "code": "retake_cooldown_active",
                                "cooldown_until": cooldown_until.isoformat(),
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                        ),
                    )

        return True, None

    def _can_user_access_blueprint(self, blueprint: ExamBlueprint, user: User) -> bool:
        if user.exam_type != blueprint.exam_type:
            return False

        if blueprint.exam_type == user.ExamType.EXIT:
            return bool(blueprint.department_id and blueprint.department_id == user.department_id)

        if blueprint.grade12_stream and blueprint.grade12_stream != user.grade12_stream:
            return False
        return True

    def _build_payload(self, questions):
        payload = []
        for q in questions:
            options = [q.option_a, q.option_b, q.option_c, q.option_d]
            correct_index = {"A": 0, "B": 1, "C": 2, "D": 3}.get((q.correct_answer or "A").upper(), 0)
            payload.append(
                {
                    "id": q.id,
                    "text": q.question_text,
                    "options": options,
                    "correct": correct_index,
                    "subject": q.subject.name,
                    "grade_level": q.subject.grade_level,
                }
            )
        return payload

    def _adaptive_pick_for_section(self, queryset, section, selected_ids):
        remaining = section.question_count
        picked_questions = []
        difficulty_order = ["easy", "medium", "hard"]

        for difficulty in difficulty_order:
            if remaining <= 0:
                break
            qs = queryset.filter(difficulty=difficulty)
            if selected_ids:
                qs = qs.exclude(id__in=selected_ids)
            # Progressively ramp by taking from easy -> medium -> hard.
            share = max(1, section.question_count // len(difficulty_order))
            target = min(remaining, share)
            chunk = list(qs.order_by("?")[:target])
            picked_questions.extend(chunk)
            selected_ids.update(q.id for q in chunk)
            remaining -= len(chunk)

        if remaining > 0:
            qs = queryset
            if selected_ids:
                qs = qs.exclude(id__in=selected_ids)
            chunk = list(qs.order_by("?")[:remaining])
            picked_questions.extend(chunk)
            selected_ids.update(q.id for q in chunk)

        return picked_questions

    def _generate_from_blueprint(self, request, base_queryset, blueprint: ExamBlueprint):
        selected_questions = []
        selected_ids = set()
        section_plan = []
        sections = blueprint.sections.select_related("subject").all().order_by("sort_order", "id")

        for section in sections:
            section_qs = base_queryset.filter(subject=section.subject)
            if section.topic:
                section_qs = section_qs.filter(topic__icontains=section.topic)
            if section.difficulty != section.DifficultyRule.ANY:
                section_qs = section_qs.filter(difficulty=section.difficulty)
            if section.source != section.SourceRule.ANY:
                section_qs = section_qs.filter(source=section.source)
            if selected_ids:
                section_qs = section_qs.exclude(id__in=selected_ids)

            if blueprint.adaptive_difficulty and section.difficulty == section.DifficultyRule.ANY:
                picked = self._adaptive_pick_for_section(section_qs, section, selected_ids)
            else:
                picked = list(section_qs.order_by("?")[: section.question_count])
                selected_ids.update(question.id for question in picked)

            selected_questions.extend(picked)

            section_key = self._section_key(section)
            section_plan.append(
                {
                    "id": section_key,
                    "label": section.subject.name,
                    "subject": section.subject.name,
                    "question_count": len(picked),
                    "duration_minutes": section.duration_minutes,
                    "pass_threshold_percentage": section.pass_threshold_percentage,
                    "sort_order": section.sort_order,
                }
            )

        # Fill missing slots from the remaining scoped pool so users always get a complete exam when possible.
        remaining_slots = max(blueprint.question_count - len(selected_questions), 0)
        if remaining_slots > 0:
            fallback_qs = base_queryset.exclude(id__in=selected_ids)
            selected_questions.extend(list(fallback_qs.order_by("?")[:remaining_slots]))

        question_payload = self._build_payload(selected_questions)

        # Attach section metadata in order so frontend can enforce timed/locked section behavior.
        cursor = 0
        for section in section_plan:
            for _ in range(section["question_count"]):
                if cursor >= len(question_payload):
                    break
                question_payload[cursor]["section_id"] = section["id"]
                question_payload[cursor]["section_label"] = section["label"]
                question_payload[cursor]["section_order"] = section["sort_order"]
                cursor += 1

        if blueprint.shuffle_questions:
            random.shuffle(question_payload)

        if blueprint.shuffle_options:
            for item in question_payload:
                self._shuffle_question_options(item)

        return {
            "questions": question_payload,
            "mode": {
                "blueprint_id": blueprint.id,
                "timed_sections": blueprint.timed_sections,
                "negative_marking_enabled": blueprint.negative_marking_enabled,
                "negative_mark_per_wrong": blueprint.negative_mark_per_wrong,
                "shuffle_questions": blueprint.shuffle_questions,
                "shuffle_options": blueprint.shuffle_options,
                "section_locking": blueprint.section_locking,
                "adaptive_difficulty": blueprint.adaptive_difficulty,
                "fail_fast_enabled": blueprint.fail_fast_enabled,
                "fail_fast_min_failed_sections": blueprint.fail_fast_min_failed_sections,
                "anti_cheat_enabled": blueprint.anti_cheat_enabled,
                "max_blur_warnings": blueprint.max_blur_warnings,
                "auto_submit_on_anti_cheat": blueprint.auto_submit_on_anti_cheat,
                "max_retake_attempts": blueprint.max_retake_attempts,
                "retake_cooldown_minutes": blueprint.retake_cooldown_minutes,
                "passing_score": blueprint.passing_score,
            },
            "sections": section_plan,
        }

    @action(detail=False, methods=["get"])
    def generate(self, request):
        count = int(request.query_params.get("count", 10))
        subject_name = request.query_params.get("subject")
        subject_id = request.query_params.get("subject_id")
        grade_level = request.query_params.get("grade_level")
        blueprint_id = request.query_params.get("blueprint_id")

        qs = scope_question_queryset_for_user(
            Question.objects.select_related("subject", "subject__department").all(),
            request.user,
        )

        if blueprint_id:
            blueprint = get_object_or_404(
                ExamBlueprint.objects.select_related("department"),
                id=blueprint_id,
                is_active=True,
            )
            if not self._can_user_access_blueprint(blueprint, request.user):
                return Response({"detail": "This exam blueprint is outside your track."}, status=status.HTTP_403_FORBIDDEN)

            allowed, error_response = self._enforce_retake_policy(blueprint, request.user)
            if not allowed:
                return error_response

            if blueprint.exam_type == request.user.ExamType.GRADE12 and blueprint.grade_level:
                qs = qs.filter(subject__grade_level=blueprint.grade_level)
            return Response(self._generate_from_blueprint(request, qs, blueprint))

        if request.user.exam_type == request.user.ExamType.GRADE12 and grade_level:
            qs = qs.filter(subject__grade_level=grade_level)

        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        if subject_name:
            qs = qs.filter(subject__name__iexact=subject_name)

        questions = list(qs.order_by("?")[:count])
        return Response(self._build_payload(questions))


class ExamBlueprintViewSet(viewsets.ModelViewSet):
    serializer_class = ExamBlueprintSerializer
    queryset = ExamBlueprint.objects.select_related("department").prefetch_related("sections__subject")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [IsAdminUserRole()]

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user

        if is_admin_principal(user):
            return qs

        qs = qs.filter(is_active=True, exam_type=user.exam_type)
        if user.exam_type == user.ExamType.EXIT:
            qs = qs.filter(department_id=user.department_id)
        elif user.grade12_stream:
            qs = qs.filter(grade12_stream__in=[None, "", user.grade12_stream])

        return qs

    @action(detail=True, methods=["get"])
    def attempts(self, request, pk=None):
        blueprint = self.get_object()
        attempts_qs = (
            ExamResult.objects.filter(blueprint=blueprint)
            .select_related("user")
            .order_by("created_at")
        )

        attempts = []
        for item in attempts_qs:
            total = max(item.total_questions, 1)
            weighted_percentage = max(0.0, (float(item.weighted_score) / float(total)) * 100.0)
            attempts.append(
                {
                    "id": item.id,
                    "user_id": item.user_id,
                    "username": item.user.username,
                    "score": item.score,
                    "weighted_score": item.weighted_score,
                    "total_questions": item.total_questions,
                    "weighted_percentage": round(weighted_percentage, 2),
                    "duration": item.duration,
                    "created_at": item.created_at,
                }
            )

        trend_qs = (
            attempts_qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                attempts=Count("id"),
                avg_score=Avg("score"),
                avg_weighted_score=Avg("weighted_score"),
            )
            .order_by("day")
        )

        trend = [
            {
                "day": str(row["day"]),
                "attempts": int(row["attempts"] or 0),
                "avg_score": round(float(row["avg_score"] or 0), 2),
                "avg_weighted_score": round(float(row["avg_weighted_score"] or 0), 2),
            }
            for row in trend_qs
        ]

        summary = {
            "attempts": attempts_qs.count(),
            "avg_score": round(float(attempts_qs.aggregate(value=Avg("score"))["value"] or 0), 2),
            "avg_weighted_score": round(float(attempts_qs.aggregate(value=Avg("weighted_score"))["value"] or 0), 2),
        }

        return Response({"summary": summary, "trend": trend, "attempts": attempts[-30:]})
