from __future__ import annotations

from rest_framework import serializers

from django_notifications.models import UserNotification


class UserNotificationSerializer(serializers.ModelSerializer[UserNotification]):
    has_action = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserNotification
        fields = (
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "read_at",
            "related_object_type",
            "related_object_id",
            "action_url",
            "metadata",
            "has_action",
            "created_at",
            "expires_at",
        )
        read_only_fields = fields

