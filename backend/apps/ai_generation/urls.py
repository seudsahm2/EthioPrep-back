from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIQuestionJobViewSet

router = DefaultRouter()
router.register(r"jobs", AIQuestionJobViewSet, basename="ai-jobs")

urlpatterns = [path("", include(router.urls))]
