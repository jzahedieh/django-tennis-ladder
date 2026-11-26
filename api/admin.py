from django.contrib import admin

from api.models import DevicePushToken, RefreshToken


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "device_label", "created_at", "expires_at", "revoked_at")
    search_fields = ("user__email", "user__username", "device_label")
    list_filter = ("revoked_at",)


@admin.register(DevicePushToken)
class DevicePushTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "is_active", "updated_at")
    search_fields = ("user__email", "user__username", "expo_push_token")
    list_filter = ("platform", "is_active")
