import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.questions.models import Department

User = get_user_model()


@pytest.mark.django_db
def test_register_and_login():
    client = APIClient()
    payload = {
        "email": "student@example.com",
        "username": "student1",
        "password": "strongpass123",
        "exam_type": "grade12",
    }
    register = client.post("/api/auth/register", payload, format="json")
    assert register.status_code == 201

    login = client.post(
        "/api/auth/login",
        {"email": payload["email"], "password": payload["password"]},
        format="json",
    )
    assert login.status_code == 200
    assert "access" in login.data


@pytest.mark.django_db
def test_exit_registration_requires_department():
    client = APIClient()
    missing_department = client.post(
        "/api/auth/register",
        {
            "email": "exit@example.com",
            "username": "exit1",
            "password": "strongpass123",
            "exam_type": "exit",
        },
        format="json",
    )
    assert missing_department.status_code == 400

    department = Department.objects.create(name="Computer Science")
    registered = client.post(
        "/api/auth/register",
        {
            "email": "exit2@example.com",
            "username": "exit2",
            "password": "strongpass123",
            "exam_type": "exit",
            "department_id": department.id,
        },
        format="json",
    )
    assert registered.status_code == 201
