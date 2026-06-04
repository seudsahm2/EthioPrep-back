from django.db import migrations, models


def _base_rich_template():
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


def default_simple_explanation_rich():
    template = _base_rich_template()
    template[0]["text"] = "Simple Explanation"
    template[8]["text"] = "Optional quick tip"
    return template


def default_detailed_explanation_rich():
    template = _base_rich_template()
    template[0]["text"] = "Detailed Explanation"
    template[8]["text"] = "Optional exam strategy"
    return template


def default_deep_explanation_rich():
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


def backfill_rich_templates(apps, schema_editor):
    Question = apps.get_model("questions", "Question")
    for question in Question.objects.all().iterator():
        changed = False
        if not question.simple_explanation_rich:
            question.simple_explanation_rich = default_simple_explanation_rich()
            changed = True
        if not question.detailed_explanation_rich:
            question.detailed_explanation_rich = default_detailed_explanation_rich()
            changed = True
        if not question.deep_explanation_rich:
            question.deep_explanation_rich = default_deep_explanation_rich()
            changed = True
        if changed:
            question.save(
                update_fields=[
                    "simple_explanation_rich",
                    "detailed_explanation_rich",
                    "deep_explanation_rich",
                ]
            )


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0005_question_rich_explanations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="simple_explanation_rich",
            field=models.JSONField(blank=True, default=default_simple_explanation_rich),
        ),
        migrations.AlterField(
            model_name="question",
            name="detailed_explanation_rich",
            field=models.JSONField(blank=True, default=default_detailed_explanation_rich),
        ),
        migrations.AlterField(
            model_name="question",
            name="deep_explanation_rich",
            field=models.JSONField(blank=True, default=default_deep_explanation_rich),
        ),
        migrations.RunPython(backfill_rich_templates, migrations.RunPython.noop),
    ]
