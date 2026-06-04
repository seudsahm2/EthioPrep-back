import re

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from utils.permissions import is_admin_principal

from apps.questions.models import Department

User = get_user_model()
GRADE12_STREAM_CHOICES = (("natural", "Natural"), ("social", "Social"))


def _normalize_username(value: str) -> str:
    cleaned = re.sub(r"[^\w.@+-]", "_", (value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:150]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    grade12_stream = serializers.ChoiceField(
        choices=GRADE12_STREAM_CHOICES,
        required=False,
        allow_null=True,
    )
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = User
        fields = ("id", "email", "username", "password", "exam_type", "grade12_stream", "department_id")

    def validate_email(self, value):
        normalized_email = (value or "").strip().lower()
        if not normalized_email:
            return None
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def validate_username(self, value):
        normalized_username = _normalize_username(value)
        if not normalized_username:
            raise serializers.ValidationError("Username cannot be empty.")
        if User.objects.filter(username__iexact=normalized_username).exists():
            raise serializers.ValidationError("This username is already taken.")
        return normalized_username

    def validate(self, attrs):
        exam_type = attrs.get("exam_type")
        department = attrs.get("department")
        grade12_stream = attrs.get("grade12_stream")

        if exam_type == "exit" and not department:
            raise serializers.ValidationError({"department_id": "Department is required for exit exam students."})
        if exam_type == "grade12":
            attrs["department"] = None
            if not grade12_stream:
                raise serializers.ValidationError({"grade12_stream": "Please choose Natural or Social."})
        if exam_type == "exit":
            attrs["grade12_stream"] = None
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        if "email" not in validated_data:
            validated_data["email"] = None
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    department_id = serializers.IntegerField(source="department.id", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    google_linked = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "role",
            "exam_type",
            "grade12_stream",
            "department_id",
            "department_name",
            "package_type",
            "created_at",
            "simple_explanations_used",
            "detailed_explanations_used",
            "deep_explanations_used",
            "google_linked",
            "email_verified",
            "is_admin",
        )
        read_only_fields = ("role", "package_type", "created_at")

    def get_google_linked(self, obj):
        return bool(getattr(obj, "google_sub", ""))

    def get_is_admin(self, obj):
        return is_admin_principal(obj)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "identifier"
    identifier = serializers.CharField(write_only=True, required=False)
    email = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "identifier" in self.fields:
            self.fields["identifier"].required = False

    def validate(self, attrs):
        raw_identifier = attrs.get("identifier") or attrs.get("email") or attrs.get("username")
        password = attrs.get("password")

        if not raw_identifier or not password:
            raise AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")

        identifier = raw_identifier.strip()
        user = None

        if "@" in identifier:
            normalized_email = identifier.lower()
            user = User.objects.filter(email__iexact=normalized_email).first()
        else:
            user = User.objects.filter(username__iexact=identifier).first()

        if not user or not user.check_password(password) or not user.is_active:
            raise AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["package_type"] = user.package_type
        return token


class ProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    grade12_stream = serializers.ChoiceField(
        choices=GRADE12_STREAM_CHOICES,
        required=False,
        allow_null=True,
    )
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = User
        fields = ("username", "email", "exam_type", "grade12_stream", "department_id")

    def validate_username(self, value):
        normalized_username = _normalize_username(value)
        if not normalized_username:
            raise serializers.ValidationError("Username cannot be empty.")
        if self.instance and User.objects.filter(username__iexact=normalized_username).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This username is already taken.")
        return normalized_username

    def validate(self, attrs):
        if "email" in attrs:
            normalized_email = (attrs.get("email") or "").strip().lower()
            attrs["email"] = normalized_email or None
            if normalized_email and User.objects.filter(email__iexact=normalized_email).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError({"email": "A user with this email already exists."})

        if "exam_type" in attrs and self.instance and attrs["exam_type"] != self.instance.exam_type:
            if self.instance.package_type != User.PackageType.FREE:
                raise serializers.ValidationError(
                    {"exam_type": "Exam type cannot be changed after purchasing a paid package."}
                )

        current_exam_type = getattr(self.instance, "exam_type", "grade12")
        current_department = getattr(self.instance, "department", None)
        current_grade12_stream = getattr(self.instance, "grade12_stream", None)
        exam_type = attrs.get("exam_type", current_exam_type)
        department = attrs.get("department", current_department)
        grade12_stream = attrs.get("grade12_stream", current_grade12_stream)

        if exam_type == "exit" and not department:
            raise serializers.ValidationError({"department_id": "Department is required for exit exam students."})
        if exam_type == "grade12":
            attrs["department"] = None
            if not grade12_stream:
                raise serializers.ValidationError({"grade12_stream": "Please choose Natural or Social."})
        if exam_type == "exit":
            attrs["grade12_stream"] = None
        return attrs

    def update(self, instance, validated_data):
        new_email = validated_data.get("email", instance.email)
        old_email = instance.email
        if (old_email or "") != (new_email or ""):
            instance.email_verified = False
            if instance.google_sub:
                instance.google_sub = None
        return super().update(instance, validated_data)
