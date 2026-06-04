import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.questions.models import Question, Subject

User = get_user_model()


@pytest.mark.django_db
def test_practice_answer_updates_score():
    user = User.objects.create_user(email="p@example.com", username="practice", password="pass12345")
    subject = Subject.objects.create(name="Math", exam_type="grade12")
    question = Question.objects.create(
        subject=subject,
        question_text="Derivative of x^2?",
        option_a="2x",
        option_b="x",
        option_c="x^2",
        option_d="1",
        correct_answer="A",
    )

    client = APIClient()
    token = client.post("/api/auth/login", {"email": "p@example.com", "password": "pass12345"}, format="json").data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    session = client.post("/api/practice/start/", {"subject": subject.id}, format="json")
    assert session.status_code == 201
    session_id = session.data.get("id") or session.data.get("session", {}).get("id")
    assert session_id is not None

    answer = client.post(
        "/api/practice/answer/",
        {"session_id": session_id, "question": question.id, "selected_option": "A"},
        format="json",
    )
    assert answer.status_code == 200
    assert answer.data["is_correct"] is True
