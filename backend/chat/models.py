from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"گفتگو #{self.pk}"


class Message(models.Model):
    ROLE_CHOICES = [("user", "کاربر"), ("assistant", "سامانه")]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()

    retrieved_chunks = models.JSONField(default=list, blank=True)
    top_score = models.FloatField(null=True, blank=True)
    backend_used = models.CharField(max_length=50, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Feedback(models.Model):
    RATING_CHOICES = [("up", "مفید"), ("down", "غیرمفید")]

    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="feedback")
    rating = models.CharField(max_length=10, choices=RATING_CHOICES)
    reason = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)