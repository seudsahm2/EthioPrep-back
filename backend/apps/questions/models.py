from django.db import models


def _base_rich_template() -> list[dict]:
    # Flexible block schema: admins can keep, edit, remove, or add new block types.
    return [
        {"type": "title", "text": ""},
        {"type": "markdown", "text": ""},
        {"type": "steps", "items": ["", "", ""]},
        {"type": "code", "language": "python", "text": ""},
        {"type": "math", "latex": ""},
        {"type": "table", "headers": ["", ""], "rows": [["", ""]]},
        {"type": "image", "url": "", "caption": ""},
        {"type": "chart", "chart_type": "line", "data": {"labels": [], "datasets": []}},
        {"type": "hint", "text": ""},
        {"type": "warning", "text": ""},
        {"type": "reference", "title": "", "url": ""},
    ]


def default_simple_explanation_rich() -> list[dict]:
    template = _base_rich_template()
    template[0]["text"] = "Simple Explanation"
    template[8]["text"] = "Optional quick tip"
    return template


def default_detailed_explanation_rich() -> list[dict]:
    template = _base_rich_template()
    template[0]["text"] = "Detailed Explanation"
    template[8]["text"] = "Optional exam strategy"
    return template


def default_deep_explanation_rich() -> list[dict]:
    template = _base_rich_template()
    template[0]["text"] = "Deep Explanation"
    template.insert(
        2,
        {
            "type": "advanced",
            "sections": [
                {"title": "Common Pitfalls", "text": ""},
                {"title": "Alternative Method", "text": ""},
                {"title": "Proof / Derivation", "text": ""},
            ],
        },
    )
    return template


def _default_block_for_type(block_type: str) -> dict:
    templates = {
        "title": {"type": "title", "text": ""},
        "markdown": {"type": "markdown", "text": ""},
        "steps": {"type": "steps", "items": ["", "", ""]},
        "code": {"type": "code", "language": "python", "text": ""},
        "math": {"type": "math", "latex": ""},
        "table": {"type": "table", "headers": ["", ""], "rows": [["", ""]]},
        "image": {"type": "image", "url": "", "caption": ""},
        "chart": {"type": "chart", "chart_type": "line", "equation": "y = x", "x_min": -10, "x_max": 10, "x_step": 0.5},
        "hint": {"type": "hint", "text": ""},
        "warning": {"type": "warning", "text": ""},
        "reference": {"type": "reference", "title": "", "url": ""},
        "advanced": {
            "type": "advanced",
            "sections": [
                {"title": "Common Pitfalls", "text": ""},
                {"title": "Alternative Method", "text": ""},
                {"title": "Proof / Derivation", "text": ""},
            ],
        },
    }
    return dict(templates.get(block_type, {"type": "markdown", "text": ""}))


def normalize_rich_blocks(value, level: str) -> list[dict]:
    if isinstance(value, dict):
        value = value.get("blocks", [])
    elif isinstance(value, str):
        text = value.strip()
        value = [{"type": "markdown", "text": text}] if text else []

    if not isinstance(value, list):
        value = []

    normalized: list[dict] = []
    for block in value:
        if isinstance(block, str):
            text = block.strip()
            if text:
                normalized.append({"type": "markdown", "text": text})
            continue
        if not isinstance(block, dict):
            continue

        block_type = str(block.get("type") or "markdown")
        safe = _default_block_for_type(block_type)
        safe.update(block)
        safe["type"] = block_type

        # Keep table data rectangular to avoid UI/render issues.
        if block_type == "table":
            headers = safe.get("headers") if isinstance(safe.get("headers"), list) else ["", ""]
            rows = safe.get("rows") if isinstance(safe.get("rows"), list) else []
            width = max(1, len(headers))
            fixed_rows = []
            for row in rows:
                row_values = row if isinstance(row, list) else []
                fixed = [str(row_values[i]) if i < len(row_values) else "" for i in range(width)]
                fixed_rows.append(fixed)
            safe["headers"] = [str(h) for h in headers]
            safe["rows"] = fixed_rows if fixed_rows else [["" for _ in range(width)]]

        normalized.append(safe)

    if normalized:
        return normalized

    defaults = {
        "simple": default_simple_explanation_rich,
        "detailed": default_detailed_explanation_rich,
        "deep": default_deep_explanation_rich,
    }
    return defaults[level]()


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Subject(models.Model):
    class ExamType(models.TextChoices):
        GRADE12 = "grade12", "Grade 12"
        EXIT = "exit", "University Exit"

    class GradeLevel(models.IntegerChoices):
        GRADE_9 = 9, "Grade 9"
        GRADE_10 = 10, "Grade 10"
        GRADE_11 = 11, "Grade 11"
        GRADE_12 = 12, "Grade 12"

    class Grade12Stream(models.TextChoices):
        NATURAL = "natural", "Natural"
        SOCIAL = "social", "Social"

    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=ExamType.choices)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subjects",
    )
    grade_level = models.PositiveSmallIntegerField(
        choices=GradeLevel.choices,
        null=True,
        blank=True,
    )
    grade12_stream = models.CharField(
        max_length=20,
        choices=Grade12Stream.choices,
        null=True,
        blank=True,
    )
    questions_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "exam_type", "department", "grade_level", "grade12_stream"],
                name="unique_subject_per_track_scope",
            )
        ]

    def __str__(self) -> str:
        if self.exam_type == self.ExamType.GRADE12 and self.grade_level:
            return f"{self.name} (Grade {self.grade_level})"
        if self.department_id:
            return f"{self.name} ({self.department.name})"
        return self.name


class Question(models.Model):
    class Source(models.TextChoices):
        PAST = "past_exam", "Past Exam"
        MODEL = "model_exam", "Model Exam"
        CLASS = "class_exam", "Class Exam"
        AI = "ai_generated", "AI Generated"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="questions")
    topic = models.CharField(max_length=120, blank=True)
    question_type = models.CharField(max_length=50, default="multiple_choice")
    question_text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)
    correct_answer = models.CharField(max_length=1)

    simple_explanation = models.TextField(blank=True)
    detailed_explanation = models.TextField(blank=True)
    deep_explanation = models.TextField(blank=True)
    simple_explanation_rich = models.JSONField(default=default_simple_explanation_rich, blank=True)
    detailed_explanation_rich = models.JSONField(default=default_detailed_explanation_rich, blank=True)
    deep_explanation_rich = models.JSONField(default=default_deep_explanation_rich, blank=True)

    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    year = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.PAST)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["difficulty"]),
            models.Index(fields=["source"]),
            models.Index(fields=["year"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.question_text[:60]

    def save(self, *args, **kwargs):
        self.simple_explanation_rich = normalize_rich_blocks(self.simple_explanation_rich, "simple")
        self.detailed_explanation_rich = normalize_rich_blocks(self.detailed_explanation_rich, "detailed")
        self.deep_explanation_rich = normalize_rich_blocks(self.deep_explanation_rich, "deep")
        super().save(*args, **kwargs)

    def _plain_from_rich(self, rich_value) -> str:
        if not rich_value:
            return ""
        if isinstance(rich_value, str):
            return rich_value
        if isinstance(rich_value, dict):
            rich_value = rich_value.get("blocks", [])
        if not isinstance(rich_value, list):
            return ""

        lines = []
        for block in rich_value:
            if isinstance(block, str):
                lines.append(block)
                continue
            if not isinstance(block, dict):
                continue
            # For unknown future block shapes, preserve text-like values if present.
            text = block.get("text") or block.get("markdown") or block.get("latex") or block.get("title")
            if text:
                lines.append(str(text))
        return "\n\n".join([line for line in lines if line]).strip()

    def get_explanation_payload(self, level: str) -> dict:
        field_map = {
            "simple": ("simple_explanation", "simple_explanation_rich"),
            "detailed": ("detailed_explanation", "detailed_explanation_rich"),
            "deep": ("deep_explanation", "deep_explanation_rich"),
        }
        plain_field, rich_field = field_map[level]
        plain_value = (getattr(self, plain_field, "") or "").strip()
        rich_value = getattr(self, rich_field, None)

        if not plain_value:
            plain_value = self._plain_from_rich(rich_value)

        return {
            "level": level,
            "explanation": plain_value,
            "rich_explanation": rich_value if rich_value else [],
        }


class Bookmark(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="bookmarks")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="bookmarked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "question")
