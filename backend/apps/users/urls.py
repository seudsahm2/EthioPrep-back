from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    GoogleOAuthCallbackView,
    GoogleLinkStartView,
    GoogleOAuthStartView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    TelegramMiniAppLoginView,
    TelegramOAuthVerifyView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("register/", RegisterView.as_view()),
    # Backward compatibility for older frontend builds still posting to /register/request.
    path("register/request", RegisterView.as_view(), name="register_request_compat"),
    path("register/request/", RegisterView.as_view()),
    path("login", LoginView.as_view(), name="login"),
    path("login/", LoginView.as_view()),
    path("logout", LogoutView.as_view(), name="logout"),
    path("logout/", LogoutView.as_view()),
    path("refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("refresh/", TokenRefreshView.as_view()),
    path("me", MeView.as_view(), name="me"),
    path("me/", MeView.as_view()),
    path("google/start", GoogleOAuthStartView.as_view(), name="google_oauth_start"),
    path("google/start/", GoogleOAuthStartView.as_view()),
    path("google/link/start", GoogleLinkStartView.as_view(), name="google_link_start"),
    path("google/link/start/", GoogleLinkStartView.as_view()),
    path("google/callback", GoogleOAuthCallbackView.as_view(), name="google_oauth_callback"),
    path("google/callback/", GoogleOAuthCallbackView.as_view()),
    path("telegram/verify", TelegramOAuthVerifyView.as_view(), name="telegram_oauth_verify"),
    path("telegram/verify/", TelegramOAuthVerifyView.as_view()),
    path("telegram/miniapp-login", TelegramMiniAppLoginView.as_view(), name="telegram_miniapp_login"),
    path("telegram/miniapp-login/", TelegramMiniAppLoginView.as_view()),
]
