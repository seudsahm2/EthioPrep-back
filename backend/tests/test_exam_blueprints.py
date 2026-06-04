import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.exams.models import ExamBlueprint, ExamBlueprintSection
from apps.questions.models import Department, Question, Subject

User = get_user_model()


@pytest.mark.django_db
def test_generate_uses_blueprint_section_rules():
    user = User.objects.create_user(
        email="student@example.com",
        username="student",
        password="pass12345",
        exam_type="grade12",
        grade12_stream="natural",
    )

    math = Subject.objects.create(
        name="Mathematics",
        exam_type="grade12",
        grade_level=12,
        grade12_stream="natural",
    )
    physics = Subject.objects.create(
        name="Physics",
        exam_type="grade12",
        grade_level=12,
        grade12_stream="natural",
    )

    for index in range(3):
        Question.objects.create(
            subject=math,
            question_text=f"Math easy {index}",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            difficulty="easy",
            source="past_exam",
        )

    Question.objects.create(
        subject=math,
        question_text="Math hard",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
        difficulty="hard",
        source="past_exam",
    )

    for index in range(2):
        Question.objects.create(
            subject=physics,
            question_text=f"Physics medium {index}",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            difficulty="medium",
            source="model_exam",
        )

    blueprint = ExamBlueprint.objects.create(
        name="Structured Grade 12 Exam",
        exam_type="grade12",
        grade12_stream="natural",
        question_count=3,
        duration_minutes=90,
        is_active=True,
    )

    ExamBlueprintSection.objects.create(
        blueprint=blueprint,
        subject=math,
        difficulty="easy",
        question_count=2,
        sort_order=1,
    )
    ExamBlueprintSection.objects.create(
        blueprint=blueprint,
        subject=physics,
        question_count=1,
        sort_order=2,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(f"/api/exam-simulation/generate/?blueprint_id={blueprint.id}")
    assert response.status_code == 200
    assert "questions" in response.data
    assert "mode" in response.data
    assert "sections" in response.data
    assert len(response.data["questions"]) == 3

    subjects = [item["subject"] for item in response.data["questions"]]
    assert subjects.count("Mathematics") == 2
    assert subjects.count("Physics") == 1


@pytest.mark.django_db
def test_generate_denies_blueprint_from_other_track():
    engineering = Department.objects.create(name="Engineering")
    health = Department.objects.create(name="Health")

    user = User.objects.create_user(
        email="exit@example.com",
        username="exit-student",
        password="pass12345",
        exam_type="exit",
        department=engineering,
    )

    health_subject = Subject.objects.create(
        name="Pharmacy",
        exam_type="exit",
        department=health,
    )
    Question.objects.create(
        subject=health_subject,
        question_text="Health question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    blueprint = ExamBlueprint.objects.create(
        name="Health Exit Exam",
        exam_type="exit",
        department=health,
        question_count=1,
        duration_minutes=60,
        is_active=True,
    )
    ExamBlueprintSection.objects.create(blueprint=blueprint, subject=health_subject, question_count=1, sort_order=1)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(f"/api/exam-simulation/generate/?blueprint_id={blueprint.id}")
    assert response.status_code == 403


@pytest.mark.django_db
def test_generate_blocks_when_retake_limit_reached():
    user = User.objects.create_user(
        email="limit@example.com",
        username="limit-user",
        password="pass12345",
        exam_type="grade12",
        grade12_stream="natural",
    )

    subject = Subject.objects.create(
        name="Chemistry",
        exam_type="grade12",
        grade_level=12,
        grade12_stream="natural",
    )
    Question.objects.create(
        subject=subject,
        question_text="Chem question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    blueprint = ExamBlueprint.objects.create(
        name="One Attempt Blueprint",
        exam_type="grade12",
        grade12_stream="natural",
        question_count=1,
        duration_minutes=30,
        max_retake_attempts=1,
        is_active=True,
    )
    ExamBlueprintSection.objects.create(blueprint=blueprint, subject=subject, question_count=1, sort_order=1)

    # Record one prior attempt.
    from apps.exams.models import ExamResult

    ExamResult.objects.create(
        user=user,
        blueprint=blueprint,
        subject="Chemistry",
        score=1,
        weighted_score=1,
        total_questions=1,
        correct_answers=1,
        wrong_answers=0,
        duration=60,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(f"/api/exam-simulation/generate/?blueprint_id={blueprint.id}")
    assert response.status_code == 429
    assert response.data["code"] == "retake_limit_reached"


@pytest.mark.django_db
def test_blueprint_attempts_endpoint_returns_summary_and_trend_for_admin():
    admin = User.objects.create_user(
        email="admin@example.com",
        username="admin-user",
        password="pass12345",
        role="admin",
        exam_type="grade12",
    )
    student = User.objects.create_user(
        email="student2@example.com",
        username="student-two",
        password="pass12345",
        exam_type="grade12",
        grade12_stream="natural",
    )

    subject = Subject.objects.create(
        name="Biology",
        exam_type="grade12",
        grade_level=12,
        grade12_stream="natural",
    )
    blueprint = ExamBlueprint.objects.create(
        name="Attempts Blueprint",
        exam_type="grade12",
        grade12_stream="natural",
        question_count=2,
        duration_minutes=30,
        is_active=True,
    )
    ExamBlueprintSection.objects.create(blueprint=blueprint, subject=subject, question_count=2, sort_order=1)

    from apps.exams.models import ExamResult

    ExamResult.objects.create(
        user=student,
        blueprint=blueprint,
        subject="Biology",
        score=2,
        weighted_score=1.75,
        total_questions=2,
        correct_answers=2,
        wrong_answers=0,
        duration=100,
    )

    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(f"/api/exam-blueprints/{blueprint.id}/attempts/")
    assert response.status_code == 200
    assert "summary" in response.data
    assert "trend" in response.data
    assert "attempts" in response.data
    assert response.data["summary"]["attempts"] == 1
