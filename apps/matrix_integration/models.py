import uuid

from django.conf import settings
from django.db import models


class MatrixGlobalRoom(models.Model):
    room_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.room_id


class MatrixDirectRoom(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matrix_direct_room",
    )
    room_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} -> {self.room_id}"


class MatrixBotConversationState(models.Model):
    class State(models.TextChoices):
        SELECTING_PATIENT = "selecting_patient", "Selecting patient"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matrix_bot_states",
    )
    room_id = models.CharField(max_length=255, unique=True)
    state = models.CharField(max_length=50, choices=State.choices)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.room_id} - {self.state}"
