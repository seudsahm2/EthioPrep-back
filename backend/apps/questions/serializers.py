from rest_framework import serializers

from .models import Bookmark, Department, Question, Subject, normalize_rich_blocks


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


class SubjectSerializer(serializers.ModelSerializer):
    department_id = serializers.IntegerField(source="department.id", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Subject
        fields = (
            "id",
            "name",
            "exam_type",
            "grade_level",
            "grade12_stream",
            "department_id",
            "department_name",
            "questions_count",
        )


class QuestionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    options = serializers.SerializerMethodField()
    option_a = serializers.CharField(write_only=True)
    option_b = serializers.CharField(write_only=True)
    option_c = serializers.CharField(write_only=True)
    option_d = serializers.CharField(write_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "subject",
            "subject_name",
            "topic",
            "question_type",
            "question_text",
            "options",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_answer",
            "simple_explanation",
            "simple_explanation_rich",
            "detailed_explanation",
            "detailed_explanation_rich",
            "deep_explanation",
            "deep_explanation_rich",
            "difficulty",
            "year",
            "source",
        )

    def get_options(self, obj):
        return [obj.option_a, obj.option_b, obj.option_c, obj.option_d]

    def validate(self, attrs):
        option_fields = ("option_a", "option_b", "option_c", "option_d")
        for field_name in option_fields:
            if field_name in attrs:
                attrs[field_name] = str(attrs[field_name]).strip()
                if not attrs[field_name]:
                    raise serializers.ValidationError({field_name: "This option cannot be empty."})

        correct_answer = str(attrs.get("correct_answer", "")).strip().upper()
        if correct_answer and correct_answer not in {"A", "B", "C", "D"}:
            raise serializers.ValidationError({"correct_answer": "Correct answer must be one of: A, B, C, D."})
        if correct_answer:
            attrs["correct_answer"] = correct_answer

        if "simple_explanation_rich" in attrs:
            attrs["simple_explanation_rich"] = normalize_rich_blocks(attrs.get("simple_explanation_rich"), "simple")
        if "detailed_explanation_rich" in attrs:
            attrs["detailed_explanation_rich"] = normalize_rich_blocks(attrs.get("detailed_explanation_rich"), "detailed")
        if "deep_explanation_rich" in attrs:
            attrs["deep_explanation_rich"] = normalize_rich_blocks(attrs.get("deep_explanation_rich"), "deep")
        return attrs


class QuestionListSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source="subject.name")
    options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ("id", "question_text", "subject", "topic", "options", "difficulty", "source")

    def get_options(self, obj):
        return [obj.option_a, obj.option_b, obj.option_c, obj.option_d]


class ExplanationSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=("simple", "detailed", "deep"))

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return instance


class BookmarkSerializer(serializers.ModelSerializer):
    question = QuestionListSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ("id", "question", "created_at")
