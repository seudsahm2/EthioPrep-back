import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.questions.models import Question, Subject

User = get_user_model()


@pytest.mark.django_db
def test_simple_limit_for_free_user():
    user = User.objects.create_user(email="u@example.com", username="u", password="pass12345")
    user.simple_explanations_used = 20
    user.save()

    subject = Subject.objects.create(name="Physics", exam_type="grade12")
    question = Question.objects.create(
        subject=subject,
        question_text="Q",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    client = APIClient()
    token = client.post("/api/auth/login", {"email": "u@example.com", "password": "pass12345"}, format="json").data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(f"/api/questions/{question.id}/explanation/", {"level": "simple"}, format="json")
    assert response.status_code == 402
