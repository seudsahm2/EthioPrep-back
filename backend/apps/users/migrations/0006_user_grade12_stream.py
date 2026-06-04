from django.db import migrations, models


def set_grade12_stream_for_existing_users(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(exam_type="grade12", grade12_stream__isnull=True).update(grade12_stream="natural")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_email_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="grade12_stream",
            field=models.CharField(
                blank=True,
                choices=[("natural", "Natural"), ("social", "Social")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(set_grade12_stream_for_existing_users, noop_reverse),
    ]
