from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="rejection_reason",
            field=models.TextField(blank=True, default=""),
        ),
    ]
