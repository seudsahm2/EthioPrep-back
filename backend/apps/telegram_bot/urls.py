from django.urls import path

from .views import TelegramStartPracticeView, TelegramSubmitAnswerView

urlpatterns = [
    path("practice/start", TelegramStartPracticeView.as_view(), name="telegram-practice-start"),
    path("practice/answer", TelegramSubmitAnswerView.as_view(), name="telegram-practice-answer"),
]
