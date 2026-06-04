from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.questions.models import Question, Subject
from apps.questions.scoping import question_belongs_to_user_track, scope_subject_queryset_for_user
from apps.users.models import StudyHistory

from .models import ExamBlueprint, ExamBlueprintSection, ExamResult, PracticeSession, UserAnswer


class PracticeSessionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = PracticeSession
        fields = (
            "id",
            "subject",
            "subject_name",
            "topic",
            "started_at",
            "completed_at",
            "score",
            "total_questions",
        )
        read_only_fields = ("started_at", "completed_at", "score", "total_questions")

    def validate_subject(self, subject):
        if subject is None:
            return subject

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None:
            return subject

        allowed = scope_subject_queryset_for_user(Subject.objects.filter(id=subject.id), user)
        if not allowed.exists():
            raise serializers.ValidationError("Selected subject is outside your exam track.")
        return subject


class UserAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAnswer
        fields = ("question", "selected_option")

    def create(self, validated_data):
        request = self.context["request"]
        session = self.context["session"]
        question = validated_data["question"]
        selected_option = validated_data["selected_option"].upper()
        is_correct = question.correct_answer.upper() == selected_option

        answer, _ = UserAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                "user": request.user,
                "selected_option": selected_option,
                "is_correct": is_correct,
            },
        )

        session.total_questions = session.answers.count()
        session.score = session.answers.filter(is_correct=True).count()
        session.save(update_fields=["total_questions", "score"])

        StudyHistory.objects.create(
            user=request.user,
            subject=question.subject.name,
            topic=question.topic,
            correct=1 if is_correct else 0,
            total=1,
        )
        return answer


class PracticeAnswerRequestSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    selected_option = serializers.ChoiceField(choices=("A", "B", "C", "D", "a", "b", "c", "d"))

    def validate(self, attrs):
        request = self.context["request"]
        question = attrs["question"]
        user = request.user

        if not question_belongs_to_user_track(question, user):
            raise serializers.ValidationError({"question": "Question is outside your exam track."})

        return attrs

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return instance


class ExamResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamResult
        fields = (
            "id",
            "blueprint",
            "subject",
            "score",
            "weighted_score",
            "total_questions",
            "correct_answers",
            "wrong_answers",
            "duration",
            "created_at",
        )
        read_only_fields = ("created_at",)


class PracticeCompleteSerializer(serializers.Serializer):
    complete = serializers.BooleanField(default=True)

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return instance

    def save(self, **kwargs):
        session = self.context["session"]
        session.completed_at = timezone.now()
        session.save(update_fields=["completed_at"])
        return session


class ExamBlueprintSectionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = ExamBlueprintSection
        fields = (
            "id",
            "subject",
            "subject_name",
            "topic",
            "difficulty",
            "source",
            "question_count",
            "duration_minutes",
            "pass_threshold_percentage",
            "sort_order",
        )


class ExamBlueprintSerializer(serializers.ModelSerializer):
    sections = ExamBlueprintSectionSerializer(many=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    total_section_questions = serializers.SerializerMethodField()

    class Meta:
        model = ExamBlueprint
        fields = (
            "id",
            "name",
            "description",
            "exam_type",
            "grade12_stream",
            "grade_level",
            "department",
            "department_name",
            "question_count",
            "duration_minutes",
            "passing_score",
            "instructions",
            "timed_sections",
            "negative_marking_enabled",
            "negative_mark_per_wrong",
            "shuffle_questions",
            "shuffle_options",
            "section_locking",
            "adaptive_difficulty",
            "fail_fast_enabled",
            "fail_fast_min_failed_sections",
            "anti_cheat_enabled",
            "max_blur_warnings",
            "auto_submit_on_anti_cheat",
            "max_retake_attempts",
            "retake_cooldown_minutes",
            "is_active",
            "sections",
            "total_section_questions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_total_section_questions(self, obj):
        return sum(section.question_count for section in obj.sections.all())

    def validate(self, attrs):
        attrs = super().validate(attrs)

        exam_type = attrs.get("exam_type", getattr(self.instance, "exam_type", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        grade12_stream = attrs.get("grade12_stream", getattr(self.instance, "grade12_stream", None))
        grade_level = attrs.get("grade_level", getattr(self.instance, "grade_level", None))

        if exam_type == Subject.ExamType.EXIT and not department:
            raise serializers.ValidationError({"department": "Exit exam blueprints require a department."})
        if exam_type == Subject.ExamType.GRADE12 and department:
            raise serializers.ValidationError({"department": "Grade 12 blueprints cannot use a department."})
        if exam_type == Subject.ExamType.EXIT and grade12_stream:
            raise serializers.ValidationError({"grade12_stream": "Exit exam blueprints cannot set grade stream."})
        if exam_type == Subject.ExamType.EXIT and grade_level:
            raise serializers.ValidationError({"grade_level": "Exit exam blueprints cannot set grade level."})

        sections = attrs.get("sections")
        if sections is None and self.instance is not None:
            sections_total = sum(section.question_count for section in self.instance.sections.all())
        else:
            sections_total = sum(section.get("question_count", 0) for section in (sections or []))

        question_count = attrs.get("question_count", getattr(self.instance, "question_count", 0))
        timed_sections = attrs.get("timed_sections", getattr(self.instance, "timed_sections", False))
        section_locking = attrs.get("section_locking", getattr(self.instance, "section_locking", False))
        shuffle_questions = attrs.get("shuffle_questions", getattr(self.instance, "shuffle_questions", False))
        fail_fast_enabled = attrs.get("fail_fast_enabled", getattr(self.instance, "fail_fast_enabled", False))
        fail_fast_min_failed_sections = attrs.get(
            "fail_fast_min_failed_sections",
            getattr(self.instance, "fail_fast_min_failed_sections", 1),
        )
        anti_cheat_enabled = attrs.get("anti_cheat_enabled", getattr(self.instance, "anti_cheat_enabled", True))
        max_blur_warnings = attrs.get("max_blur_warnings", getattr(self.instance, "max_blur_warnings", 3))
        negative_marking_enabled = attrs.get(
            "negative_marking_enabled",
            getattr(self.instance, "negative_marking_enabled", False),
        )
        negative_mark_per_wrong = attrs.get(
            "negative_mark_per_wrong",
            getattr(self.instance, "negative_mark_per_wrong", 0),
        )
        if sections_total <= 0:
            raise serializers.ValidationError({"sections": "At least one section with questions is required."})
        if question_count and sections_total > question_count:
            raise serializers.ValidationError({"sections": "Section total cannot exceed exam question count."})
        if timed_sections:
            if sections is None and self.instance is not None:
                missing_duration = any(not section.duration_minutes for section in self.instance.sections.all())
            else:
                missing_duration = any(not section.get("duration_minutes") for section in (sections or []))
            if missing_duration:
                raise serializers.ValidationError({"sections": "Timed sections require duration on every section."})

        section_thresholds = []
        if sections is None and self.instance is not None:
            section_thresholds = [section.pass_threshold_percentage for section in self.instance.sections.all()]
        else:
            section_thresholds = [section.get("pass_threshold_percentage") for section in (sections or [])]

        for threshold in section_thresholds:
            if threshold is not None and not (1 <= int(threshold) <= 100):
                raise serializers.ValidationError({"sections": "Section pass threshold must be between 1 and 100."})

        if fail_fast_enabled and not any(threshold is not None for threshold in section_thresholds):
            raise serializers.ValidationError({"sections": "Fail-fast mode requires pass threshold on at least one section."})
        if fail_fast_min_failed_sections < 1:
            raise serializers.ValidationError({"fail_fast_min_failed_sections": "Must be at least 1."})
        if anti_cheat_enabled and max_blur_warnings < 1:
            raise serializers.ValidationError({"max_blur_warnings": "Must be at least 1."})

        if section_locking and shuffle_questions:
            raise serializers.ValidationError({"shuffle_questions": "Disable question shuffling when section locking is enabled."})
        if timed_sections and shuffle_questions:
            raise serializers.ValidationError({"shuffle_questions": "Disable question shuffling when timed sections are enabled."})
        if negative_marking_enabled and negative_mark_per_wrong <= 0:
            raise serializers.ValidationError({"negative_mark_per_wrong": "Set a positive value for negative marking."})

        return attrs

    def _save_sections(self, blueprint: ExamBlueprint, sections_data: list[dict]):
        blueprint.sections.all().delete()
        for raw in sections_data:
            section = ExamBlueprintSection(blueprint=blueprint, **raw)
            try:
                section.full_clean()
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
            section.save()

    def create(self, validated_data):
        sections_data = validated_data.pop("sections", [])
        request = self.context.get("request")
        blueprint = ExamBlueprint(**validated_data)
        if request and request.user and request.user.is_authenticated:
            blueprint.created_by = request.user
        try:
            blueprint.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        blueprint.save()
        self._save_sections(blueprint, sections_data)
        return blueprint

    def update(self, instance, validated_data):
        sections_data = validated_data.pop("sections", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        instance.save()

        if sections_data is not None:
            self._save_sections(instance, sections_data)

        return instance
