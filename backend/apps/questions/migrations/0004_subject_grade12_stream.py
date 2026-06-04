from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0003_department_alter_subject_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="grade12_stream",
            field=models.CharField(
                blank=True,
                choices=[("natural", "Natural"), ("social", "Social")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="subject",
            name="unique_subject_per_track_scope",
        ),
        migrations.AddConstraint(
            model_name="subject",
            constraint=models.UniqueConstraint(
                fields=("name", "exam_type", "department", "grade_level", "grade12_stream"),
                name="unique_subject_per_track_scope",
            ),
        ),
    ]
