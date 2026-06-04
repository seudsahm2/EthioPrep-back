from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0004_subject_grade12_stream"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="deep_explanation_rich",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="question",
            name="detailed_explanation_rich",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="question",
            name="simple_explanation_rich",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
