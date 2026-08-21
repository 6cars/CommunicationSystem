import uuid

from django.db import models


class CounselingSession(models.Model):
    PHASE_INITIAL = "initial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_phase = models.CharField(max_length=64, default=PHASE_INITIAL)
    state_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.id} ({self.current_phase})"


class Message(models.Model):
    SENDER_USER = "user"
    SENDER_AGENT = "agent"
    SENDER_CHOICES = [
        (SENDER_USER, "user"),
        (SENDER_AGENT, "agent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        CounselingSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    sender = models.CharField(max_length=16, choices=SENDER_CHOICES)
    content = models.TextField()
    strategy_log = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.content[:40]}"
