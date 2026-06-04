from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from utils.permissions import IsAdminUserRole, is_admin_principal

from .models import AIQuestionJob
from .serializers import AIQuestionJobSerializer
from .tasks import generate_questions_task


class AIQuestionJobViewSet(viewsets.ModelViewSet):
    serializer_class = AIQuestionJobSerializer

    def get_queryset(self):
        if is_admin_principal(self.request.user):
            return AIQuestionJob.objects.select_related("subject").all()
        return AIQuestionJob.objects.select_related("subject").filter(user=self.request.user)

    def get_permissions(self):
        if self.action == "create":
            return [IsAdminUserRole()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(user=request.user, status=AIQuestionJob.Status.PENDING)
        generate_questions_task.delay(job.id)
        return Response(self.get_serializer(job).data, status=status.HTTP_201_CREATED)
