from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BadgeDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(max_length=240)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("streak", "Streak"),
                            ("practice", "Practice"),
                            ("exam", "Exam"),
                            ("accuracy", "Accuracy"),
                            ("points", "Points"),
                            ("milestone", "Milestone"),
                        ],
                        default="milestone",
                        max_length=20,
                    ),
                ),
                ("points_reward", models.PositiveIntegerField(default=0)),
                ("sort_order", models.PositiveIntegerField(default=100)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="GamificationProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points", models.PositiveIntegerField(default=0)),
                ("current_streak", models.PositiveIntegerField(default=0)),
                ("best_streak", models.PositiveIntegerField(default=0)),
                ("last_activity_date", models.DateField(blank=True, null=True)),
                ("practice_answered", models.PositiveIntegerField(default=0)),
                ("practice_correct", models.PositiveIntegerField(default=0)),
                ("practice_sessions", models.PositiveIntegerField(default=0)),
                ("exam_attempts", models.PositiveIntegerField(default=0)),
                ("exam_answered", models.PositiveIntegerField(default=0)),
                ("exam_correct", models.PositiveIntegerField(default=0)),
                ("perfect_exams", models.PositiveIntegerField(default=0)),
                ("total_answered", models.PositiveIntegerField(default=0)),
                ("total_correct", models.PositiveIntegerField(default=0)),
                ("badges_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="gamification_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-points", "-best_streak", "user_id"]},
        ),
        migrations.CreateModel(
            name="PointTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=120)),
                ("points", models.IntegerField()),
                ("source_type", models.CharField(blank=True, max_length=50)),
                ("source_id", models.PositiveIntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="point_transactions", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="UserBadge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("earned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "badge",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="earned_by", to="analytics.badgedefinition"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="badges", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-earned_at"], "unique_together": {("user", "badge")}},
        ),
    ]
