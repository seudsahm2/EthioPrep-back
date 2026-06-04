import hashlib
import hmac
import json
import logging
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from utils.permissions import IsAdminUserRole

from .serializers import (
    CustomTokenObtainPairSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class SocialAccountConflictError(ValueError):
    """Raised when social sign-in email belongs to a password-based account."""


def _oauth_username(base_username: str) -> str:
    normalized = re.sub(r"[^\w.@+-]", "_", (base_username or "").strip()).strip("_")
    candidate = (normalized or "user")[:140]
    if not User.objects.filter(username=candidate).exists():
        return candidate

    suffix = 1
    while True:
        trimmed = candidate[:130]
        new_name = f"{trimmed}_{suffix}"
        if not User.objects.filter(username=new_name).exists():
            return new_name
        suffix += 1


def _issue_tokens_for_user(user) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def _build_frontend_redirect(provider: str, payload: dict[str, str]) -> str:
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    params = urlencode({"oauth": provider, **payload})
    return f"{frontend_url}/auth?{params}"


def _google_json_request(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None and method.upper() == "GET":
        query = urlencode(payload)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"
    elif payload is not None:
        body = urlencode(payload).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = Request(url=url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_or_create_oauth_user(email: str, username_hint: str):
    normalized_email = email.strip().lower()
    existing = User.objects.filter(email__iexact=normalized_email).first()
    if existing:
        if existing.has_usable_password():
            raise SocialAccountConflictError(
                "Email already belongs to a password account. Login with username/password first."
            )
        return existing, False

    username = _oauth_username(username_hint)
    user = User(email=normalized_email, username=username)
    user.set_unusable_password()
    user.save()
    return user, True


class RegisterView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    def post(self, _request):
        return Response({"detail": "Logout successful. Remove token on client side."})


class MeView(GenericAPIView):
    serializer_class = ProfileUpdateSerializer

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = self.get_serializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class GoogleOAuthStartView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, _request):
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "")
        if not client_id or not redirect_uri:
            return Response(
                {"detail": "Google OAuth is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "select_account",
            }
        )
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
        return redirect(auth_url)


class GoogleLinkStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "")
        if not client_id or not redirect_uri:
            return Response(
                {"detail": "Google OAuth is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        signer = TimestampSigner(salt="google-link")
        state = signer.sign(str(request.user.id))
        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
        return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)


class GoogleOAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code:
            error_redirect = _build_frontend_redirect("google", {"oauth_error": "Missing code"})
            return redirect(error_redirect)

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
        redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "")
        if not client_id or not client_secret or not redirect_uri:
            error_redirect = _build_frontend_redirect("google", {"oauth_error": "Google OAuth not configured"})
            return redirect(error_redirect)

        try:
            token_data = _google_json_request(
                "https://oauth2.googleapis.com/token",
                method="POST",
                payload={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            access_token = token_data.get("access_token", "")
            if not access_token:
                raise ValueError("Missing access token")

            user_info = _google_json_request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                payload={"access_token": access_token},
            )
            email = user_info.get("email")
            if not email:
                raise ValueError("Google account does not provide email")

            google_sub = str(user_info.get("sub") or "")
            if not google_sub:
                raise ValueError("Google account does not provide unique id")

            # Link flow: user is already logged in and explicitly connecting Google.
            if state:
                signer = TimestampSigner(salt="google-link")
                try:
                    user_id = int(signer.unsign(state, max_age=300))
                except (BadSignature, SignatureExpired, ValueError) as exc:
                    raise ValueError("Invalid or expired link state") from exc

                user = User.objects.filter(id=user_id).first()
                if not user:
                    raise ValueError("Link target account not found")
                if not user.email:
                    raise ValueError("Please set your email in Profile before linking Google")
                if user.email.strip().lower() != email.strip().lower():
                    raise ValueError("Google email must match your account email to link")
                if User.objects.filter(google_sub=google_sub).exclude(id=user.id).exists():
                    raise ValueError("This Google account is already linked elsewhere")

                user.email = email.strip().lower()
                user.google_sub = google_sub
                user.email_verified = True
                user.save(update_fields=["email", "google_sub", "email_verified"])
                return redirect(f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')}/profile?linked=google")

            username_hint = user_info.get("name") or email.split("@")[0]
            normalized_email = email.strip().lower()
            existing = User.objects.filter(email__iexact=normalized_email).first()
            if existing:
                if existing.has_usable_password() and not existing.google_sub:
                    raise ValueError("Email already belongs to a password account. Login first, then connect Google from Profile.")
                if existing.google_sub and existing.google_sub != google_sub:
                    raise ValueError("This account is linked to a different Google account.")
                user = existing
                created = False
            else:
                user, created = _get_or_create_oauth_user(email=normalized_email, username_hint=username_hint)

            if not user.google_sub:
                if User.objects.filter(google_sub=google_sub).exclude(id=user.id).exists():
                    raise ValueError("This Google account is already linked to another user.")
                user.google_sub = google_sub
                user.save(update_fields=["google_sub"])

            tokens = _issue_tokens_for_user(user)
            payload = {**tokens, "onboarding": "1" if created else "0"}
            return redirect(_build_frontend_redirect("google", payload))
        except (ValueError, HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.exception("Google OAuth callback failed")
            error_redirect = _build_frontend_redirect(
                "google",
                {"oauth_error": f"Google sign-in failed: {str(exc)[:120]}"},
            )
            return redirect(error_redirect)


class TelegramOAuthVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        received_hash = str(data.get("hash", ""))
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            return Response(
                {"detail": "Telegram OAuth is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not received_hash:
            return Response({"detail": "Missing Telegram hash."}, status=status.HTTP_400_BAD_REQUEST)

        payload_items = {
            key: str(value)
            for key, value in data.items()
            if key in {"id", "first_name", "last_name", "username", "photo_url", "auth_date"} and value is not None
        }
        check_string = "\n".join(f"{k}={payload_items[k]}" for k in sorted(payload_items.keys()))
        secret = hashlib.sha256(bot_token.encode("utf-8")).digest()
        calculated_hash = hmac.new(secret, check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return Response({"detail": "Invalid Telegram signature."}, status=status.HTTP_400_BAD_REQUEST)

        telegram_id = payload_items.get("id")
        username_hint = payload_items.get("username") or f"telegram_{telegram_id}"
        email = f"telegram_{telegram_id}@telegram.local"
        try:
            user, created = _get_or_create_oauth_user(email=email, username_hint=username_hint)
        except SocialAccountConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        tokens = _issue_tokens_for_user(user)

        return Response(
            {
                **tokens,
                "onboarding_required": created,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class TelegramMiniAppLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        init_data_raw = str(data.get("init_data") or "").strip()
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            return Response(
                {"detail": "Telegram Mini App auth is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not init_data_raw:
            return Response({"detail": "Missing Telegram init_data."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse Telegram initData query-string safely.
        pairs = parse_qsl(init_data_raw, keep_blank_values=True)
        payload = {key: value for key, value in pairs}
        received_hash = payload.pop("hash", "")
        if not received_hash:
            return Response({"detail": "Missing Telegram hash in init_data."}, status=status.HTTP_400_BAD_REQUEST)

        data_check_string = "\n".join(f"{key}={payload[key]}" for key in sorted(payload.keys()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return Response({"detail": "Invalid Telegram Mini App signature."}, status=status.HTTP_400_BAD_REQUEST)

        auth_date_raw = payload.get("auth_date", "")
        try:
            auth_date = int(auth_date_raw)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid Telegram auth_date."}, status=status.HTTP_400_BAD_REQUEST)

        max_age_seconds = int(getattr(settings, "TELEGRAM_MINIAPP_AUTH_MAX_AGE_SECONDS", 86400))
        if int(time.time()) - auth_date > max_age_seconds:
            return Response({"detail": "Telegram Mini App session is too old. Reopen the app from Telegram."}, status=status.HTTP_400_BAD_REQUEST)

        user_blob = payload.get("user", "")
        try:
            user_payload = json.loads(user_blob) if user_blob else {}
        except json.JSONDecodeError:
            return Response({"detail": "Invalid Telegram user payload."}, status=status.HTTP_400_BAD_REQUEST)

        telegram_id = str(user_payload.get("id") or "").strip()
        if not telegram_id:
            return Response({"detail": "Telegram user id is missing."}, status=status.HTTP_400_BAD_REQUEST)

        username_hint = str(user_payload.get("username") or f"telegram_{telegram_id}")
        email = f"telegram_{telegram_id}@telegram.local"
        try:
            user, created = _get_or_create_oauth_user(email=email, username_hint=username_hint)
        except SocialAccountConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        tokens = _issue_tokens_for_user(user)
        return Response(
            {
                **tokens,
                "onboarding_required": created,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-created_at")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAdminUserRole()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)
