from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.analytics.views import AnalyticsViewSet
from apps.exams.views import ExamBlueprintViewSet, ExamResultViewSet, PracticeSessionViewSet
from apps.payments.views import PaymentViewSet
from apps.questions.views import QuestionViewSet, SubjectViewSet
from apps.users.views import UserViewSet

router = DefaultRouter()
router.register(r"subjects", SubjectViewSet, basename="subjects")
router.register(r"questions", QuestionViewSet, basename="questions")
router.register(r"practice", PracticeSessionViewSet, basename="practice")
router.register(r"exam-simulation", ExamResultViewSet, basename="exam-simulation")
router.register(r"exam-blueprints", ExamBlueprintViewSet, basename="exam-blueprints")
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"analytics", AnalyticsViewSet, basename="analytics")
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls")),
    path("api/ai/", include("apps.ai_generation.urls")),
    path("api/telegram/", include("apps.telegram_bot.urls")),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
