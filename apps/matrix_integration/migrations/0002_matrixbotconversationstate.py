from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("matrix_integration", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MatrixBotConversationState",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("room_id", models.CharField(max_length=255, unique=True)),
                (
                    "state",
                    models.CharField(
                        choices=[("selecting_patient", "Selecting patient")],
                        max_length=50,
                    ),
                ),
                ("data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matrix_bot_states",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
