from django.db import migrations, models


def mark_existing_emails_verified(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.exclude(email__isnull=True).exclude(email="").update(email_verified=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_alter_user_email_delete_pendingregistration"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_emails_verified, noop_reverse),
    ]
