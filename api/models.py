from django.conf import settings
from django.db import models
from django.utils import timezone


class RefreshToken(models.Model):
    """Opaque hashed refresh token enabling rolling rotation and server-side revocation."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_refresh_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    device_label = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
        ]

    def __str__(self):
        return f"RefreshToken(user_id={self.user_id}, device={self.device_label or 'unknown'})"

    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()


class DevicePushToken(models.Model):
    """Stores Expo push tokens registered by mobile and web clients."""

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"
        WEB = "web", "Web"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_tokens",
    )
    expo_push_token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform}:{self.user_id}"
