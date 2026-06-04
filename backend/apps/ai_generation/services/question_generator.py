from apps.questions.models import Question
from services.ai_service import AIService


class AIQuestionGenerator:
    def __init__(self) -> None:
        self.ai_service = AIService()

    def generate_and_save(self, *, subject, topic: str, count: int, difficulty: str) -> int:
        generated = self.ai_service.generate_questions(
            subject=subject.name,
            topic=topic or None,
            count=count,
            difficulty=difficulty,
        )
        created = 0
        for row in generated:
            Question.objects.create(
                subject=subject,
                topic=topic,
                question_text=row["question_text"],
                option_a=row["option_a"],
                option_b=row["option_b"],
                option_c=row["option_c"],
                option_d=row["option_d"],
                correct_answer=row["correct_answer"],
                simple_explanation=row["simple_explanation"],
                detailed_explanation=row["detailed_explanation"],
                deep_explanation=row["deep_explanation"],
                difficulty=difficulty if difficulty in {"easy", "medium", "hard"} else "medium",
                source=Question.Source.AI,
            )
            created += 1
        return created
