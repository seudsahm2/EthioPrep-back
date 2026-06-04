import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.questions.models import Question, Subject

User = get_user_model()


@pytest.mark.django_db
def test_grade12_generate_can_filter_by_grade_level():
    user = User.objects.create_user(
        email="grade12@example.com",
        username="g12",
        password="pass12345",
        exam_type="grade12",
    )

    grade9_subject = Subject.objects.create(name="Mathematics", exam_type="grade12", grade_level=9)
    grade12_subject = Subject.objects.create(name="Physics", exam_type="grade12", grade_level=12)

    Question.objects.create(
        subject=grade9_subject,
        question_text="G9 question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )
    Question.objects.create(
        subject=grade12_subject,
        question_text="G12 question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    client = APIClient()
    token = client.post(
        "/api/auth/login",
        {"email": "grade12@example.com", "password": "pass12345"},
        format="json",
    ).data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get("/api/exam-simulation/generate/?count=10&grade_level=9")
    assert response.status_code == 200
    assert response.data
    assert all(item.get("grade_level") == 9 for item in response.data)
