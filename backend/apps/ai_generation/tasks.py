from celery import shared_task

from .models import AIQuestionJob
from .services.question_generator import AIQuestionGenerator


@shared_task(bind=True)
def generate_questions_task(self, job_id: int) -> None:
    job = AIQuestionJob.objects.select_related("subject").get(id=job_id)
    job.status = AIQuestionJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        generator = AIQuestionGenerator()
        generator.generate_and_save(
            subject=job.subject,
            topic=job.topic,
            count=job.count,
            difficulty=job.difficulty,
        )
        job.status = AIQuestionJob.Status.COMPLETED
        job.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        job.status = AIQuestionJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise
